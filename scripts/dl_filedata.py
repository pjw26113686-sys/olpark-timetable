import sys, json, re, subprocess, urllib.parse
def run(args): return subprocess.run(['curl','-sS','-m','120']+args,capture_output=True)
pk=sys.argv[1]; out=sys.argv[2]
html=run([f'https://www.data.go.kr/data/{pk}/fileData.do']).stdout.decode('utf-8','ignore')
m=re.search(r"fn_fileDataDown\('(\d+)',\s*'([^']+)'",html)
if not m: print(pk,'no download fn'); sys.exit(1)
r=run(['https://www.data.go.kr/tcs/dss/selectFileDataDownload.do','--data-urlencode',f'publicDataPk={pk}','--data-urlencode',f'publicDataDetailPk={m.group(2)}','--data-urlencode','atchFileId=','--data-urlencode','fileDetailSn=1','--data-urlencode','publicDataTyCode=PR0051'])
j=json.loads(r.stdout); a=j['atchFileId']; s=j['fileDetailSn']; nm=j['dataSetFileDetailInfo'].get('dataNm','')
lim=run(['https://www.data.go.kr/cmm/cmm/check-limit.json','--data-urlencode',f'atchFileId={a}','--data-urlencode',f'fileDetailSn={s}']).stdout[:200]
url=f"https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId={a}&fileDetailSn={s}&dataNm={urllib.parse.quote(nm)}"
d=run(['-L','-o',out,url])
print(pk,nm,lim,d.returncode)
