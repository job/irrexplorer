from irrexplorer.nrtm import client
a = client(nrtmhost='whois.radb.net',
           nrtmport=43,
           serial='ftp://ftp.radb.net/radb/dbase/RADB.CURRENTSERIAL',
           dump='ftp://ftp.radb.net/radb/dbase/radb.db.gz',
           dbase="RADB")

while True:
    for i in a.get():
        print i
