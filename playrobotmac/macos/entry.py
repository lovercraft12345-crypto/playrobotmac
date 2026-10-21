"""Entrada del .app y de sus utilidades USB; no vuelve a abrir la interfaz."""
import os
import json
from pathlib import Path
import runpy
import sys

def smoke_test(report_path):
    from main import PlayRobotESP32
    errors=[]
    app=PlayRobotESP32()
    app.report_callback_exception=lambda kind,value,tb:errors.append(str(value))
    app.after(1500,app.quit)
    app.mainloop()
    panel=getattr(app,'account_window',None)
    opened=panel is not None and bool(panel.winfo_exists())
    app.destroy()
    result={'ui_started':opened,'errors':errors,'platform':sys.platform}
    Path(report_path).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    if errors or not opened:raise SystemExit(1)

def main():
    if len(sys.argv)==3 and sys.argv[1]=='--self-test':
        smoke_test(sys.argv[2])
        return
    if len(sys.argv)>2 and sys.argv[1]=='-m':
        module=sys.argv[2]
        if module not in {'mpremote','esptool'}:
            raise SystemExit('Utilidad no permitida')
        sys.argv=[module,*sys.argv[3:]]
        # Las utilidades seriales necesitan sus flujos aunque Finder no los cree.
        for name,fd,mode in [('stdin',0,'r'),('stdout',1,'w'),('stderr',2,'w')]:
            if getattr(sys,name) is None:
                setattr(sys,name,os.fdopen(os.dup(fd),mode,encoding='utf-8',errors='replace'))
        runpy.run_module(module,run_name='__main__')
        return
    from main import PlayRobotESP32
    app=PlayRobotESP32()
    app.mainloop()

if __name__=='__main__':main()
