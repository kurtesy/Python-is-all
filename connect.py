import cx_Oracle
#con = cx_Oracle.connect('bia_dw/bia_dw@HSCSRV136.allegisgroup.com:1522/ORCL.allegisgroup.com')
con = cx_Oracle.connect('bia_dw/bia_dw@10.188.193.136:1522/ORCL.allegisgroup.com')
print con.version
con.close()

