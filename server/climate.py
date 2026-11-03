"""Dopasowanie miesiaca do celu: dane klimatyczne zamiast obietnic."""
import geo
def month(d,m):
    c=d.get('climate')
    if not c: return None
    i=m-1
    g=lambda k:(c.get(k) or [None]*12)[i]
    return {'tmax':g('tmax'),'tmin':g('tmin'),'rain':g('rain'),'sea':g('sea')}
def fit(d,m,style):
    """0..1 oraz powod. None = brak danych, wtedy nie udajemy wiedzy."""
    c=month(d,m)
    if not c or c['tmax'] is None: return None,'Brak danych klimatycznych'
    t,s,r=c['tmax'],c['sea'],c['rain'] or 0
    if style=='beach':
        if s is None: return 0.05,f'Brak dostępu do morza w danych, {round(t)}°C'
        v=min(1,max(0,(t-16)/8))*0.6+min(1,max(0,(s-15)/7))*0.4
        if t<20 or s<18: why=f'Za zimno na plażowanie: {round(t)}°C, morze {round(s)}°C'
        else: why=f'{round(t)}°C, morze {round(s)}°C'
        return round(v-min(.1,r/1000),2),why
    if style=='ski':
        return round(min(1,max(0,(9-t)/7)),2),f'{round(t)}°C w dzień'
    v=1-min(1,abs(t-22)/16)-min(.25,r/400)
    return round(max(0,v),2),f'{round(t)}°C w dzień'+(f', opady {round(r)} mm' if c['rain'] is not None else '')
