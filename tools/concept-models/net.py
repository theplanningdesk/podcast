import math, itertools, json, sys
def hav(a,b):
    R=6371; la1,lo1=map(math.radians,a); la2,lo2=map(math.radians,b)
    h=math.sin((la2-la1)/2)**2+math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return 2*R*math.asin(math.sqrt(h))
C={ # name: (lat, lon, country, weight)
'Stockholm':(59.33,18.07,'SE',10),'Gothenburg':(57.71,11.97,'SE',6),'Malmö':(55.60,13.00,'SE',5),'Uppsala':(59.86,17.64,'SE',2),
'Västerås':(59.61,16.55,'SE',1.5),'Örebro':(59.27,15.21,'SE',1.5),'Linköping':(58.41,15.62,'SE',1.5),'Jönköping':(57.78,14.16,'SE',1.5),
'Norrköping':(58.59,16.19,'SE',1.3),'Umeå':(63.83,20.26,'SE',1.2),'Sundsvall':(62.39,17.31,'SE',1),'Luleå':(65.58,22.15,'SE',1),
'Gävle':(60.67,17.14,'SE',1),'Karlstad':(59.38,13.50,'SE',1),'Växjö':(56.88,14.81,'SE',0.9),'Helsingborg':(56.05,12.69,'SE',1.4),
'Oslo':(59.91,10.75,'NO',7),'Bergen':(60.39,5.32,'NO',3),'Trondheim':(63.43,10.39,'NO',2),'Stavanger':(58.97,5.73,'NO',2),
'Kristiansand':(58.15,8.00,'NO',1),'Drammen':(59.74,10.20,'NO',1),'Tromsø':(69.65,18.96,'NO',0.8),
'Helsinki':(60.17,24.94,'FI',8),'Tampere':(61.50,23.76,'FI',2.5),'Turku':(60.45,22.27,'FI',2),'Oulu':(65.01,25.47,'FI',1.5),
'Jyväskylä':(62.24,25.75,'FI',1.2),'Kuopio':(62.89,27.68,'FI',1),
'Copenhagen':(55.68,12.57,'DK',8),'Aarhus':(56.16,10.20,'DK',3),'Odense':(55.40,10.39,'DK',2),'Aalborg':(57.05,9.92,'DK',1.5),
}
CAND=['Malmö','Gothenburg','Jönköping','Stockholm','Oslo','Helsinki','Copenhagen','Örebro']
TODAY=['Malmö','Gothenburg','Stockholm','Oslo','Helsinki']
def dist(dc,c):
    d=hav(C[dc][:2],C[c][:2])*1.3
    a,b=C[dc][2],C[c][2]
    if {a,b}=={'SE','FI'} or {a,b}=={'FI','NO'} or {a,b}=={'FI','DK'}: d+=250  # ferry crossing
    return d
TOTW=sum(v[3] for v in C.values())
def cost(sites, tr=1.0):
    fixed=2.1*len(sites)              # €M a year per DC
    inv=3.0*math.sqrt(len(sites))     # €M, square-root law
    trans=0
    assign={}
    for c,v in C.items():
        dc=min(sites,key=lambda s:dist(s,c)); assign[c]=dc
        trans+=v[3]*dist(dc,c)
    trans=trans/TOTW*0.040*tr  # €M: avg km x factor
    inbound=0.35*len(sites)
    return dict(total=fixed+inv+trans+inbound, fixed=fixed, inv=inv, trans=trans, inbound=inbound, assign=assign)
def best(n,tr=1.0):
    return min((cost(list(s),tr)['total'],list(s)) for s in itertools.combinations(CAND,n))
for tr in (1.0,1.3):
    print('tr',tr,'today',round(cost(TODAY,tr)['total'],2))
    for n in range(1,7):
        t,s=best(n,tr); print(n,round(t,2),s)
