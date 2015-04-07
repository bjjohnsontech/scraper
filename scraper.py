#! /usr/bin/python

import requests
import bs4
import re
import datetime
import pg

conn = pg.connect(
        host='localhost',
        dbname='bidFTA',
        user='postgres'
    )
cons = pg.DB(host='localhost',
        dbname='bidFTA',
        user='postgres')

known = [x[0] for x in conn.query('SELECT num FROM auctions').getresult()]

def cull():
    print conn.query('DELETE FROM auctions WHERE datetime < now()')

def getListings(listings, site, auction):
    items = []
    for listing in listings.select('.DataRow'):
        try:
            id = int(listing.attrs.get('id'))
        except ValueError:
            #print listing.attrs.get('id')
            continue
        if id == 0:
            continue
        tds = listing.select('td')
        info = re.split(r'<br\s*/>', str(tds[2]))
        INFO = {'auction': auction, 'id': id}
        for x in info:
            try:
                key, val = re.sub(r'<.{1,3}>', '', x).split(': ')
                if key.lower() in ['brand', 'item description', 'additional information']:
                    if key.lower() == 'item description':
                        INFO['description'] = val.strip()
                    elif key.lower() == 'additional information':
                        INFO['info'] = val.strip()
                    else:
                        INFO[key.lower()] = val.strip()
            except ValueError:
                continue
        INFO['image'] = tds[1].select('img')[0].attrs.get('src')
        INFO['link'] = site + tds[1].select('a')[0].attrs.get('href')
        items.append(INFO)
    return items

def main():
    response = requests.get('http://bidfta.com')
    
    soup = bs4.BeautifulSoup(response.text.replace(u'\u2019',''))
    aucs = {}
    auctions = (a for a in soup.select('div.content.active div.currentAuctionsListings div.auction'))
    for auction in auctions:
        title = auction.select('a div.auctionTitle h4')[0].get_text().split()
        #print 'Auction#:', title[0]
        
        if title[0] not in aucs:
            aucs[title[0]] = {'listings': []}
        #print 'Title:', ' '.join(title[2:])
        aucs[title[0]]['title'] = ' '.join(title[2:])
        #print 'Location:', auction.select('a .auctionLocation')[0].get_text()
        aucs[title[0]]['location'] = auction.select('a .auctionLocation')[0].get_text()
        #print 'Datetime:', auction.select('time')[0].attrs.get('datetime')
        # strip timezone
        aucs[title[0]]['datetime'] = datetime.datetime.strptime(auction.select('time')[0].attrs.get('datetime')[:-5], "%Y-%m-%dT%H:%M:%S")
        # if auction already over, ignore
        if (aucs[title[0]]['datetime'] < datetime.datetime.now()
        or int(title[0]) in known):
            continue
        aucIns = {'num': title[0], 'title': aucs[title[0]]['title'].replace(u'\u2019',''), 'location': aucs[title[0]]['location'],
                     'datetime': aucs[title[0]]['datetime']
        }
        cons.insert('auctions', aucIns)
        aucID = conn.query('SELECT id FROM auctions WHERE num=%s' % (aucIns['num'])).getresult()[0][0]
        link = auction.select('a')[0].attrs.get('href')
        site = '/'.join(link.split('/')[0:3])
        details = requests.get(link).text
        soup = bs4.BeautifulSoup(details)
        #print 'Removal:', details.split('REMOVAL: ')[1].split('<p>')[0]
        aucSite = site + soup.select('a')[6].attrs.get('href')
        listings = bs4.BeautifulSoup(requests.get(aucSite).text)
        # get next page
        aucs[title[0]]['listings'].extend(getListings(listings, site, aucID))
        try:
            form = listings.select('form[name=viewform]')[0]
        except IndexError:
            continue
        data = {
            'auction': form.select('[name=auction]')[0].attrs.get('value'),
            'contents': form.select('[name=contents]')[0].attrs.get('value'),
            'pages':form.select('[name=pages]')[0].attrs.get('value'),
            'searchtitle':form.select('[name=searchtitle]')[0].attrs.get('value'),
            'searchcount':form.select('[name=searchcount]')[0].attrs.get('value')
        }
        
        for i in range(int(data['pages'])):
            page = form.select('[name=p%d]' % (i+1))[0]
            data[page.attrs.get('name')] = page.attrs.get('value')
        for i in range(int(data['pages'])-1):
            data['page'] = 'p%s' % (i+2)
            data['npage'] = 'p%s' % (i+1)
            nextP = requests.post(aucSite, data=data).text
            listings = bs4.BeautifulSoup(nextP)
            aucs[title[0]]['listings'].extend(getListings(listings, site, aucID))
        print 'Auction: %s, %d listings' % (title[0], len(aucs[title[0]]['listings']))
        for items in aucs[title[0]]['listings']:
            try:
                cons.insert('items', items)
            except:
                continue
    
if __name__ == '__main__':
    main()
    
    #html = '''<input type="submit" name="page"></input><input type="hidden" name="page"></input>'''
    #soup = bs4.BeautifulSoup(html)
    #print soup.select('input[type=submit]')
    form = '''<form action="/cgi-bin/mnlist.cgi" method="post" name="viewform">
<br/><table align="center" border="0" id="SelectPage" width="100%"><tr><td align="center">
<input name="auction" type="hidden" value="twomc184"/>
<input name="contents" type="hidden" value="0/A/B/C/D/E/1/2/3/4/5/6/7/8/9/10/11/12/13/14/15/16/17/18/19/20/21/22/23/24/25/26/27/28/29/30/31/32/33/34/35/36/37/38/39/40/41/42/43/44/"/>
<input name="pages" type="hidden" value="3"/>
<input name="searchtitle" type="hidden" value="Category:-ALL"/>
<input name="searchcount" type="hidden" value="106"/>
<input name="page" type="hidden" value="p1"/>
<p align="center">Select page to view:
<input name="p1" type="hidden" value="0/A/B/C/D/E/1/2/3/4/5/6/7/8/9/10/11/12/13/14/15/16/17/18/19/20/21/22/23/24/25/26/27/28/29/30/31/32/33/34/35/36/37/38/39/40/41/42/43/44/"/> <u>p1</u>
<input name="p2" type="hidden" value="45/46/47/48/49/50/51/52/53/54/55/56/57/58/59/60/61/62/63/64/65/66/67/68/69/70/71/72/73/74/75/76/77/78/79/80/81/82/83/84/85/86/87/88/89/90/91/92/93/94/"/> <input name="page" type="submit" value="p2"/>
<input name="p3" type="hidden" value="95/96/97/98/99/100/"/> <input name="page" type="submit" value="p3"/>
<input name="npage" type="hidden" value="p2"/>
<input name="nwpage" type="hidden" value=""/> </p></td></tr>
</table>
</form>'''
    #form = bs4.BeautifulSoup(form)
    #for i in range(3):
    #    page = form.select('[name=p%d]' % (i+1))[0]
    #    print
    #    print 'VALUE:', page.attrs.get('value')
    #    print
    '''<tr class="DataRow" id="1" valign="top"><td><a href="/cgi-bin/mnlist.cgi?twomc198/1">1</a></td>
<td align="center"><a href="/cgi-bin/mnlist.cgi?twomc198/1"><img alt="1t.jpg" border="0" src="https://fast-track-auctions.s3.amazonaws.com/uploads/auctions/198/1t.jpg"/></a></td><td><b>Brand</b>: DIVERSEY<br/><b>Item Description</b>: CASE OF 6 SIGNATURE ULTRA HIGH SPEED FLOOR FINISH, EACH INDIVIDUAL PACKAGE CONTAINS 2.5L!<br/><b>Retail</b>: $119.99 <br/><b>Location</b>: MW-BY FRONT OFFICE<br/><b>Additional Information</b>: 6X YOUR BID, New- Item is new in or out of the box and will have no damage, missing parts or pieces.<br/><b>Contact</b>: Please use our contact submission via bidfta.com to submit any questions regarding this auction.<br/><b>Front Page</b>: <a href="http://www.bidfta.com" target="_blank">Click here to go back to Fast Track Auction Home Page</a> <br/></td>
<td align="right"><a href="/cgi-bin/mnhistory.cgi?twomc198/1">6</a></td>
<td align="right">78232</td>
<td align="right">4.20
<br/>x 6 = 25.20</td>
<td align="right">??</td>
<td align="center" colspan="2">ended</td></tr>'''

    '''
<tr class="DataRow" id="1" valign="top">
    <td>
        <a href="/cgi-bin/mnlist.cgi?twomc198/1">1</a>
    </td>
    <td align="center">
        <a href="/cgi-bin/mnlist.cgi?twomc198/1">
            <img alt="1t.jpg" border="0" src="https://fast-track-auctions.s3.amazonaws.com/uploads/auctions/198/1t.jpg"/>
        </a>
    </td>
    <td>
        <b>Brand</b>: DIVERSEY<br/>
        <b>Item Description</b>: CASE OF 6 SIGNATURE ULTRA HIGH SPEED FLOOR FINISH, EACH INDIVIDUAL PACKAGE CONTAINS 2.5L!<br/>
        <b>Retail</b>: $119.99 <br/>
        <b>Location</b>: MW-BY FRONT OFFICE<br/>
        <b>Additional Information</b>: 6X YOUR BID, New- Item is new in or out of the box and will have no damage, missing parts or pieces.<br/>
        <b>Contact</b>: Please use our contact submission via bidfta.com to submit any questions regarding this auction.<br/>
        <b>Front Page</b>: <a href="http://www.bidfta.com" target="_blank">Click here to go back to Fast Track Auction Home Page</a> <br/>
    </td>
    <td align="right"><a href="/cgi-bin/mnhistory.cgi?twomc198/1">6</a></td>
    <td align="right">78232</td>
    <td align="right">4.20
    <br/>x 6 = 25.20</td>
    <td align="right">??</td>
    <td align="center" colspan="2">ended</td>
</tr>
'''
