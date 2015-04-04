#! /usr/bin/python
import sys, json
import pg

from flask import Flask, request
app = Flask(__name__)
app.config['DEBUG'] = True
app.config['TESTING'] = True
@app.route('/')
def root():
    return "There's nothing here"

@app.route("/auctions", methods=['get'])
def getAuctions():
    #try:
    sys.path.append('/var/www/html/codeprojects/lights/')
    #return json.dumps(sys.path)
    import solve
    return solve.solution(request.form['grid'])
    #except Exception, err:
    #    return jsonify(err)

@app.route("/items", methods=['get'])
def items():
    conn = connect()
    things = conn.query('SELECT '
                        'auctions.num as auction, '
                        'auctions.datetime as datetime, '
                        'auctions.location as location, '
                        'items.link as link, '
                        'items.image as image, '
                        'items.description as desc, '
                        'items.info as info, '
                        'items.id as id '
                        'FROM items, auctions '
                        'WHERE items.auction=auctions.id').dictresult()
    return json.dumps(things)

def connect():
    return pg.connect(
        host='localhost',
        dbname='bidFTA',
        user='postgres'
    )
if __name__ == "__main__":
    app.run()