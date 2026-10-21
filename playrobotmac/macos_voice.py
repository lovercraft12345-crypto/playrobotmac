"""Selección explícita de una voz española instalada en macOS."""
import re

def spanish_voice(output):
    voices=[]
    for line in output.splitlines():
        match=re.match(r'^(.+?)\s+(es_[A-Z]{2})\s+#',line)
        if match:voices.append((match[1].strip(),match[2]))
    for preferred in ('Paulina','Mónica','Monica'):
        for name,locale in voices:
            if name == preferred or name.startswith(preferred+' ('):return name
    # No usar la voz predeterminada, que podría estar en inglés.
    return None
