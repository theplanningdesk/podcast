import random, statistics as st, json, sys
random.seed(7)
W=26; L=2
base=[1000+random.gauss(0,55) for _ in range(W+12)]
def promo(d):
    d=d[:]; 
    for t in (12+17,12+18): d[t]*=1.4
    return d
def tier(inp, ma=6, L=2, z=1.65):
    # order-up-to with moving-average forecast
    out=[]; prevS=None
    for t in range(len(inp)):
        hist=inp[max(0,t-ma+1):t+1]
        F=sum(hist)/len(hist)
        sd=st.pstdev(inp[max(0,t-ma+1):t+1]) if t>=1 else 55
        S=F*(L+1)+z*sd*(L+1)**.5
        o=inp[t]+(S-prevS if prevS is not None else 0)
        prevS=S; out.append(max(0,o))
    return out
def run(d, shared):
    store=tier(d)
    if shared:
        # DC plans on shopper sales with a longer, shared forecast; orders follow sell-out
        dc=tier(d, ma=8, z=1.0)
    else:
        dc=tier(store)
    return store, dc
res={}
for name,d in [('base',base),('promo',promo(base))]:
    for shared in (False,True):
        s,f=run(d,shared)
        s,f,dd=s[12:],f[12:],d[12:]
        sd0=st.pstdev(dd)
        res[f'{name}-{"shared" if shared else "silo"}']=dict(
            sales=[round(x) for x in dd], store=[round(x) for x in s], factory=[round(x) for x in f],
            swing_store=round(st.pstdev(s)/sd0,2), swing_factory=round(st.pstdev(f)/sd0,2), peak=round(max(f)))
for k,v in res.items(): print(k, v['swing_store'], v['swing_factory'], v['peak'], max(v['sales']))
json.dump(res, open(sys.argv[1],'w'))
