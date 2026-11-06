import json, sys, itertools
FAM='ABCD'
def co(a,b):
    if a==b: return 0
    return 1.5 if FAM.index(b)>FAM.index(a) else 4.0
orders=[ # id, fam, hours, due, release
 (1,'A',8,26,0),(2,'C',7,34,0),(3,'B',6,40,0),(4,'D',8,50,0),(5,'A',7,58,0),(6,'C',6,64,0),
 (7,'B',8,74,0),(8,'D',7,82,0),(9,'A',6,86,0),(10,'B',7,92,0),(11,'C',8,100,0),(12,'D',8,108,0)]
def run(seq, start_fam='A'):
    t=0; last=start_fam; out=[]; chg=0
    for o in seq:
        c=co(last,o[1]); 
        if c: out.append(dict(kind='co',start=t,dur=c)); 
        t+=c; chg+=c
        t=max(t,o[4]); out.append(dict(kind='job',id=o[0],fam=o[1],start=t,dur=o[2],due=o[3],late=t+o[2]>o[3]+1e-9)); t+=o[2]; last=o[1]
    return out,chg,sum(1 for x in out if x['kind']=='job' and x['late']),t
def dp(ords):
    n=len(ords); INF=1e9; best={}; 
    best[(0,-1)]=(0,None)
    for mask in range(1<<n):
        for last in range(-1,n):
            if (mask,last) not in best: continue
            t,_=best[(mask,last)]
            lf='A' if last<0 else ords[last][1]
            for j in range(n):
                if mask>>j&1: continue
                s=max(t+co(lf,ords[j][1]),ords[j][4]); e=s+ords[j][2]
                if e>ords[j][3]+1e-9: continue
                k=(mask|1<<j,j)
                if k not in best or e<best[k][0]: best[k]=(e,(mask,last))
    full=(1<<n)-1; cands=[(best[(full,j)][0],j) for j in range(n) if (full,j) in best]
    e,j=min(cands); seq=[]; k=(full,j)
    while k[1]>=0: seq.append(ords[k[1]]); k=best[k][1]
    return seq[::-1]
edd=sorted(orders,key=lambda o:o[3])
b=run(edd); print('EDD chg',b[1],'late',b[2],'end',b[3])
opt=dp(orders); o=run(opt); print('OPT chg',o[1],'late',o[2],'end',o[3], ''.join(x[1] for x in opt))
rush=(13,'C',6,88,48)
opt2=dp(orders+[rush]); r=run(opt2); print('RUSH chg',r[1],'late',r[2],'end',r[3], ''.join(x[1] for x in opt2))
eddr=run(sorted(orders+[rush],key=lambda o:o[3])); print('EDD+rush',eddr[1],eddr[2])
json.dump(dict(base=b[0],opt=o[0],rush=r[0],kpi=dict(chg=[b[1],o[1],r[1]],late=[b[2],o[2],r[2]])),open(sys.argv[1],'w'))
