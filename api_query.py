import requests
from datetime import datetime
import json
import parsedata

def get_tuple(postcode):
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
    r = requests.get("https://api.carbonintensity.org.uk/regional/intensity/" + timestamp + "/fw48h/postcode/" + postcode)

    outfile = open("data.json","w")
    outfile.write(r.text)
    outfile.close()

    infile = open("data.json","r")
    data = json.loads(infile.read())
    infile.close()

    response = []

    for d in data['data']['data']:
        timefrom = d['from']
        intensity = d['intensity']['forecast']
        response.append((timefrom,intensity))

    return response

data_tuples = get_tuple("M15")

parsedata.writecsv(data_tuples)

