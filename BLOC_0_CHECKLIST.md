# 🔥 BLOC 0 — BOOTSTRAP LOCAL — CHECKLIST VALIDATION

**Objectif** : Valider que l'UI fonctionne et qu'on peut lancer un backtest depuis l'UI.

**⚠️ CRITIQUE** : On ne passe PAS au BLOC suivant tant que ce bloc n'est pas 100% validé.

---

## ✅ ÉTAPE 0.1 — POSITIONNEMENT (OBLIGATOIRE)

**Commande à exécuter :**
```powershell
cd C:\bots\dexterio1-main
Get-Location
```

**Résultat attendu :**
```
Path
----
C:\bots\dexterio1-main
```

**Si différent :** Corriger le chemin et réessayer.

---

## ✅ ÉTAPE 0.2 — VÉRIFIER PYTHON

**Commande :**
```powershell
python --version
```

**Résultat attendu :** `Python 3.11.x` ou supérieur

**Si erreur :** Installer Python 3.11+ depuis python.org

---

## ✅ ÉTAPE 0.3 — ACTIVER LE VENV

**Commande :**
```powershell
.\.venv\Scripts\Activate.ps1
```

**Résultat attendu :** Le prompt affiche `(.venv)` au début

**Si erreur "execution policy" :**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Puis réessayer.

---

## ✅ ÉTAPE 0.4 — VÉRIFIER DÉPENDANCES

**Commande :**
```powershell
python -c "import fastapi, uvicorn, pandas, pydantic; print('✅ Dependencies OK')"
```

**Résultat attendu :** `✅ Dependencies OK`

**Si erreur "Module not found" :**
```powershell
pip install -r requirements.txt
```
Puis réessayer la vérification.

---

## ✅ ÉTAPE 0.5 — VÉRIFIER DONNÉES HISTORIQUES

**Commande :**
```powershell
python -c "import sys; sys.path.insert(0, 'backend'); from utils.path_resolver import historical_data_path; spy = historical_data_path('1m', 'SPY.parquet'); print(f'SPY data: {spy.exists()} at {spy}')"
```

**Résultat attendu :**
```
SPY data: True at C:\bots\dexterio1-main\data\historical\1m\SPY.parquet
```

**Si False :** Les données ne sont pas présentes. Le backtest échouera, mais on peut quand même tester l'UI.

---

## ✅ ÉTAPE 0.6 — LANCER LE BACKEND (TERMINAL 1)

**Ouvrir un NOUVEAU terminal PowerShell**

**Dans ce nouveau terminal :**
```powershell
cd C:\bots\dexterio1-main
.\.venv\Scripts\Activate.ps1
cd backend
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

**Résultat attendu :**
```
INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
INFO:     Started reloader process [XXXXX] using WatchFiles
INFO:     Started server process [XXXXX]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**⚠️ Si erreur MongoDB :** C'est NORMAL. MongoDB est optionnel. Les routes `/api/backtests` fonctionnent sans MongoDB.

**Test rapide (dans un 3ème terminal) :**
```powershell
curl http://localhost:8001/api/
```

**Résultat attendu :** `{"message":"Hello World"}`

**⚠️ Garder ce terminal ouvert !**

---

## ✅ ÉTAPE 0.7 — LANCER LE FRONTEND (TERMINAL 2)

**Ouvrir un NOUVEAU terminal PowerShell**

**Dans ce nouveau terminal :**
```powershell
cd C:\bots\dexterio1-main\frontend
```

**Vérifier yarn :**
```powershell
yarn --version
```

**Si erreur "yarn not found" :**
```powershell
npm install -g yarn
```

**Installer les dépendances (si pas déjà fait) :**
```powershell
yarn install
```

**Lancer le frontend :**
```powershell
yarn start
```

**Résultat attendu :**
```
Compiled successfully!

You can now view frontend in the browser.

  Local:            http://localhost:3000
  On Your Network:  http://192.168.x.x:3000
```

**⚠️ Garder ce terminal ouvert !**

---

## ✅ ÉTAPE 0.8 — ACCÉDER À L'UI

1. **Ouvrir le navigateur**
2. **Aller sur :** http://localhost:3000
3. **Naviguer vers :** http://localhost:3000/backtests

**Résultat attendu :**
- Page "Backtests" s'affiche
- Formulaire avec :
  - Symbol (dropdown SPY/QQQ)
  - Start Date (date picker)
  - End Date (date picker)
  - Trading Mode (SAFE/AGGRESSIVE)
  - Trade Types (checkboxes DAILY/SCALP)
  - HTF Warmup Days
  - Commission Model
  - Initial Capital
  - Bouton "Run Backtest"

**Si page blanche ou erreur :**
- Vérifier la console du navigateur (F12)
- Vérifier que le backend tourne (étape 0.6)
- Vérifier que le frontend tourne (étape 0.7)

---

## ✅ ÉTAPE 0.9 — LANCER UN BACKTEST

**Dans l'UI :**

1. **Remplir le formulaire :**
   - Symbol: **SPY**
   - Start Date: **2025-08-01** (ou une date où vous avez des données)
   - End Date: **2025-08-01** (même date = 1 jour)
   - Trading Mode: **SAFE**
   - Trade Types: **DAILY** (cocher)
   - HTF Warmup: **40**
   - Commission Model: **IBKR Fixed**
   - Initial Capital: **50000**

2. **Cliquer sur "Run Backtest"**

**Résultat attendu :**
- Un `job_id` apparaît (ex: `a1b2c3d4`)
- Section "Job: {job_id}" s'affiche
- Statut passe de `queued` → `running` → `done` (ou `failed`)
- Si `done` :
  - Métriques s'affichent (total_trades, total_R_net, winrate, etc.)
  - Section "Downloads" avec liens (summary, trades, equity)

**Si erreur "Un job est déjà en cours" :**
- Attendre que le job précédent se termine
- Ou vérifier les jobs dans "Recent Jobs"

**Si statut `failed` :**
- Vérifier la section "Error" pour le message
- Vérifier les logs du backend (terminal 1)

---

## ✅ ÉTAPE 0.10 — VÉRIFIER LES ARTEFACTS SUR DISQUE

**Dans un terminal PowerShell (nouveau ou existant) :**

```powershell
cd C:\bots\dexterio1-main
.\.venv\Scripts\Activate.ps1
```

**Remplacer `JOB_ID` par le job_id affiché dans l'UI :**
```powershell
$jobId = "a1b2c3d4"  # ⚠️ REMPLACER PAR VOTRE JOB_ID
python -c "import sys; sys.path.insert(0, 'backend'); from utils.path_resolver import results_path; from pathlib import Path; job_dir = results_path('jobs', '$jobId'); print(f'Job dir: {job_dir}'); print(f'Exists: {job_dir.exists()}'); files = [f.name for f in job_dir.iterdir() if f.is_file()]; print('Files:'); [print(f'  - {f}') for f in files]"
```

**Résultat attendu :**
```
Job dir: C:\bots\dexterio1-main\backend\results\jobs\a1b2c3d4
Exists: True
Files:
  - job.json
  - job.log
  - summary.json
  - trades.parquet
  - equity.parquet
```

**Si fichiers manquants :**
- Vérifier les logs du backend
- Vérifier le statut du job dans l'UI
- Vérifier que le backtest s'est bien terminé

---

## ✅ ÉTAPE 0.11 — TÉLÉCHARGER UN ARTEFACT

**Dans l'UI :**

1. **Cliquer sur le lien "summary"** dans la section Downloads
2. **Le fichier `summary.json` doit se télécharger**

**Vérifier le contenu (optionnel) :**
```powershell
# Ouvrir le fichier téléchargé
Get-Content "$env:USERPROFILE\Downloads\summary.json" | ConvertFrom-Json | Select-Object total_trades, total_R_net, winrate, profit_factor
```

**Résultat attendu :** JSON avec des métriques valides

---

## ✅ VALIDATION FINALE — CHECKLIST

Cocher chaque point :

- [ ] **Backend démarre** sans erreur (port 8001)
- [ ] **Frontend démarre** sans erreur (port 3000)
- [ ] **UI accessible** sur http://localhost:3000/backtests
- [ ] **Formulaire s'affiche** correctement
- [ ] **Backtest se lance** (job_id créé)
- [ ] **Statut passe à "done"** (ou "failed" avec raison claire)
- [ ] **Métriques s'affichent** (si done)
- [ ] **Liens de téléchargement fonctionnent** (si done)
- [ ] **Fichiers présents sur disque** (job.json, summary.json, trades.parquet, equity.parquet)

---

## 🚨 SI PROBLÈME

**Me donner :**
1. **Le message d'erreur exact** (copier-coller)
2. **À quelle étape** ça bloque (0.1, 0.2, etc.)
3. **Les logs du backend** (terminal 1)
4. **Les logs du frontend** (terminal 2)
5. **La console du navigateur** (F12 → Console)

---

## ✅ SI TOUT EST VALIDÉ

**Alors on peut passer au BLOC 1 : Audit factuel PHASE C**

---

**FIN BLOC 0**


