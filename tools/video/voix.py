#!/usr/bin/env python3
"""La Brique : choisir et écouter une voix ElevenLabs.

  python3 tools/video/voix.py chercher [mots]     voix masculines françaises de la bibliothèque, avec extrait
  python3 tools/video/voix.py essai ID "texte" sortie.mp3 [modele]   fait dire un texte à une voix (payant, quelques centimes)
La clé vient de ELEVENLABS_API_KEY ou du trousseau du Mac (service « elevenlabs »). Elle n'est jamais affichée.
"""
import json, sys, urllib.parse, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reel import cle_elevenlabs  # noqa: E402

API = "https://api.elevenlabs.io"


def get(chemin, **p):
    req = urllib.request.Request(f"{API}{chemin}?{urllib.parse.urlencode(p)}", headers={"xi-api-key": cle_elevenlabs(), "User-Agent": "LaBrique/1.0"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def chercher(mots=""):
    d = get("/v1/shared-voices", language="fr", gender="male", page_size=40, sort="trending", search=mots)
    for v in d.get("voices", []):
        print(f"{v['voice_id']}  {v.get('name','')[:40]:40}  {v.get('accent','')[:12]:12}  {v.get('age','')[:12]:12}  {v.get('use_case','')[:16]:16}  {v.get('cloned_by_count',0):>6}")
        print(f"    {(v.get('description') or '')[:140]}")
        print(f"    extrait : {v.get('preview_url')}")


def essai(voix_id, texte, sortie, modele="eleven_v3"):
    corps = {"text": texte, "model_id": modele, "voice_settings": {"stability": 0.5, "similarity_boost": 0.8, "style": 0.3, "use_speaker_boost": True}}
    req = urllib.request.Request(f"{API}/v1/text-to-speech/{voix_id}?output_format=mp3_44100_128", data=json.dumps(corps).encode(), method="POST",
                                 headers={"xi-api-key": cle_elevenlabs(), "Content-Type": "application/json", "User-Agent": "LaBrique/1.0"})
    Path(sortie).write_bytes(urllib.request.urlopen(req, timeout=120).read())
    print("ok", sortie)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["chercher"]:
        chercher(" ".join(a[1:]))
    elif a[:1] == ["essai"] and len(a) >= 4:
        essai(*a[1:5])
    else:
        sys.exit(__doc__)
