"""Informacje praktyczne dla obywatela RP. Dokumenty zawsze z odeslaniem do MSZ, bo przepisy sie zmieniaja."""
EU_ID='Dowód osobisty lub paszport'
PASS='Paszport'
C={
'IT':('Włochy','EUR','euro','F, L','włoski','+39',EU_ID),'ES':('Hiszpania','EUR','euro','C, F','hiszpański','+34',EU_ID),'PT':('Portugalia','EUR','euro','C, F','portugalski','+351',EU_ID),
'FR':('Francja','EUR','euro','C, E','francuski','+33',EU_ID),'DE':('Niemcy','EUR','euro','C, F','niemiecki','+49',EU_ID),'AT':('Austria','EUR','euro','C, F','niemiecki','+43',EU_ID),
'NL':('Holandia','EUR','euro','C, F','niderlandzki','+31',EU_ID),'BE':('Belgia','EUR','euro','C, E','niderlandzki, francuski','+32',EU_ID),'CH':('Szwajcaria','CHF','frank szwajcarski','C, J','niemiecki, francuski, włoski','+41',EU_ID),
'CZ':('Czechy','CZK','korona czeska','C, E','czeski','+420',EU_ID),'SK':('Słowacja','EUR','euro','C, E','słowacki','+421',EU_ID),'HU':('Węgry','HUF','forint','C, F','węgierski','+36',EU_ID),
'SI':('Słowenia','EUR','euro','C, F','słoweński','+386',EU_ID),'HR':('Chorwacja','EUR','euro','C, F','chorwacki','+385',EU_ID),'GR':('Grecja','EUR','euro','C, F','grecki','+30',EU_ID),
'CY':('Cypr','EUR','euro','G','grecki, turecki','+357',EU_ID),'MT':('Malta','EUR','euro','G','maltański, angielski','+356',EU_ID),'IE':('Irlandia','EUR','euro','G','angielski, irlandzki','+353',EU_ID),
'GB':('Wielka Brytania','GBP','funt','G','angielski','+44',PASS+' oraz elektroniczne zezwolenie ETA'),'NO':('Norwegia','NOK','korona norweska','C, F','norweski','+47',EU_ID),'SE':('Szwecja','SEK','korona szwedzka','C, F','szwedzki','+46',EU_ID),
'DK':('Dania','DKK','korona duńska','C, E, F, K','duński','+45',EU_ID),'FI':('Finlandia','EUR','euro','C, F','fiński, szwedzki','+358',EU_ID),'IS':('Islandia','ISK','korona islandzka','C, F','islandzki','+354',EU_ID),
'EE':('Estonia','EUR','euro','C, F','estoński','+372',EU_ID),'LV':('Łotwa','EUR','euro','C, F','łotewski','+371',EU_ID),'LT':('Litwa','EUR','euro','C, F','litewski','+370',EU_ID),'PL':('Polska','PLN','złoty','C, E','polski','+48',EU_ID),
'BG':('Bułgaria','EUR','euro','C, F','bułgarski','+359',EU_ID),'RO':('Rumunia','RON','lej rumuński','C, F','rumuński','+40',EU_ID),
'ME':('Czarnogóra','EUR','euro','C, F','czarnogórski','+382',EU_ID+' (sprawdź wymogi)'),'BA':('Bośnia i Hercegowina','BAM','marka zamienna','C, F','bośniacki','+387',EU_ID+' (sprawdź wymogi)'),
'RS':('Serbia','RSD','dinar serbski','C, F','serbski','+381',EU_ID+' (sprawdź wymogi)'),'AL':('Albania','ALL','lek','C, F','albański','+355',EU_ID+' (sprawdź wymogi)'),'MK':('Macedonia Północna','MKD','denar','C, F','macedoński','+389',EU_ID+' (sprawdź wymogi)'),
'MD':('Mołdawia','MDL','lej mołdawski','C, F','rumuński','+373',PASS),'TR':('Turcja','TRY','lira turecka','C, F','turecki','+90',PASS),'GE':('Gruzja','GEL','lari','C, F','gruziński','+995',PASS),'MA':('Maroko','MAD','dirham','C, E','arabski, francuski','+212',PASS)}
EMERG={'GB':'999 lub 112','MA':'19 (policja), 15 (pogotowie)','TR':'112','GE':'112'}
def info(cc):
    c=C.get(cc)
    if not c: return None
    return {'name':c[0],'currency':c[1],'currencyName':c[2],'plugs':c[3],'language':c[4],'dial':c[5],'docs':c[6],'emergency':EMERG.get(cc,'112'),
      'plugNote':'Polska ma wtyczki C i E. Weź adapter.' if 'C' not in c[3] else 'Polska ładowarka powinna pasować.',
      'msz':'https://www.gov.pl/web/dyplomacja/informacje-dla-podrozujacych','ekuz':cc in 'IT ES PT FR DE AT NL BE CH CZ SK HU SI HR GR CY MT IE NO SE DK FI IS EE LV LT BG RO'.split()}
