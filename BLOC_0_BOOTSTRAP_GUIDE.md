# 🔥 BLOC 0 — BOOTSTRAP LOCAL (VALIDATION UI + BACKTEST)

**Objectif** : Valider que l'environnement local fonctionne et qu'on peut lancer un backtest depuis l'UI.

---

## ✅ ÉTAPE 1 : Vérifier l'environnement

**Commande à exécuter :**
```powershell
python --version
```

**Résultat attendu :** `Python 3.11.x` ou supérieur

**Si erreur :** Installer Python 3.11+ depuis python.org

---

## ✅ ÉTAPE 2 : Activer le venv

**Commande à exécuter :**
```powershell
.\.venv\Scripts\Activate.ps1
```

**Résultat attendu :** Le prompt PowerShell affiche `(.venv)` au début

**Si erreur "execution policy" :**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Puis réessayer l'activation.

---

## ✅ ÉTAPE 3 : Vérifier/Installer les dépendances

**Commande à exécuter :**
```powershell
pip list | Select-String "fastapi|uvicorn|pandas|pydantic"
```

**Résultat attendu :** Liste des packages installés

**Si packages manquants :**
```powershell
pip install -r requirements.txt
```

**Validation :**
```powershell
python -c "import fastapi, uvicorn, pandas, pydantic; print('✅ All dependencies OK')"
```

**Résultat attendu :** `✅ All dependencies OK`

---

## ✅ ÉTAPE 4 : Vérifier les données historiques

**Commande à exécuter :**
```powershell
python -c "from utils.path_resolver import historical_data_path; from pathlib import Path; spy = historical_data_path('1m', 'SPY.parquet'); print(f'SPY data: {spy.exists()} at {spy}')"
```

**Résultat attendu :** `SPY data: True at C:\bots\dexterio1-main\data\historical\1m\SPY.parquet`

**Si False :** Les données ne sont pas présentes. Pour tester, on peut utiliser une date fictive, mais le backtest échouera.

---

## ✅ ÉTAPE 5 : Lancer le serveur backend

**Ouvrir un NOUVEAU terminal PowerShell** (garder le premier pour le frontend)

**Dans le nouveau terminal :**
```powershell
cd C:\bots\dexterio1-main
.\.venv\Scripts\Activate.ps1
cd backend
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

**Résultat attendu :**
```
INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**⚠️ Si erreur MongoDB :** C'est normal, MongoDB est maintenant optionnel. Les routes `/api/backtests` fonctionnent sans MongoDB.

**Test rapide :**
```powershell
# Dans un 3ème terminal
curl http://localhost:8001/api/
```

**Résultat attendu :** `{"message":"Hello World"}`

---

## ✅ ÉTAPE 6 : Lancer le frontend

**Dans le PREMIER terminal (ou un nouveau) :**
```powershell
cd C:\bots\dexterio1-main\frontend
yarn install
```

**Puis :**
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

**Si erreur "yarn not found" :**
```powershell
npm install -g yarn
```

---

## ✅ ÉTAPE 7 : Accéder à l'UI et lancer un backtest

1. **Ouvrir le navigateur :** http://localhost:3000
2. **Naviguer vers :** http://localhost:3000/backtests
3. **Remplir le formulaire :**
   - Symbol: SPY
   - Start Date: Choisir une date où vous avez des données (ex: 2025-08-01)
   - End Date: Même date (1 jour)
   - Trading Mode: SAFE
   - Trade Types: DAILY (cocher)
   - HTF Warmup: 40
   - Commission Model: IBKR Fixed
   - Initial Capital: 50000
4. **Cliquer sur "Run Backtest"**

**Résultat attendu :**
- Un `job_id` apparaît (ex: `a1b2c3d4`)
- Le statut passe de `queued` → `running` → `done`
- Les métriques s'affichent (total_trades, total_R_net, etc.)
- Des liens de téléchargement apparaissent (summary, trades, equity)

---

## ✅ ÉTAPE 8 : Vérifier les artefacts sur disque

**Commande à exécuter :**
```powershell
# Remplacer JOB_ID par le job_id affiché dans l'UI
$jobId = "a1b2c3d4"  # À adapter
python -c "from utils.path_resolver import results_path; from pathlib import Path; job_dir = results_path('jobs', '$jobId'); print(f'Job dir: {job_dir}'); print(f'Exists: {job_dir.exists()}'); [print(f'  {f.name}') for f in job_dir.iterdir() if f.is_file()]"
```

**Résultat attendu :**
```
Job dir: C:\bots\dexterio1-main\backend\results\jobs\a1b2c3d4
Exists: True
  job.json
  job.log
  summary.json
  trades.parquet
  equity.parquet
```

**Si fichiers manquants :** Vérifier les logs du backend pour voir l'erreur.

---

## ✅ ÉTAPE 9 : Télécharger et vérifier un artefact

**Dans l'UI :**
1. Cliquer sur le lien "summary" dans la section Downloads
2. Le fichier `summary.json` doit se télécharger

**Vérifier le contenu :**
```powershell
# Ouvrir le fichier téléchargé ou depuis le disque
Get-Content "C:\Users\VotreNom\Downloads\summary.json" | ConvertFrom-Json | Select-Object -First 5
```

**Résultat attendu :** JSON avec des métriques (total_trades, total_R_net, etc.)

---

## ✅ VALIDATION FINALE

**Checklist :**
- [ ] Backend démarre sans erreur (port 8001)
- [ ] Frontend démarre sans erreur (port 3000)
- [ ] UI accessible sur http://localhost:3000/backtests
- [ ] Formulaire de backtest s'affiche
- [ ] Backtest se lance (job_id créé)
- [ ] Statut passe à "done"
- [ ] Métriques s'affichent (total_R_net, winrate, etc.)
- [ ] Liens de téléchargement fonctionnent
- [ ] Fichiers présents sur disque (summary.json, trades.parquet, equity.parquet)

**Si TOUT est ✅ :** Passer au BLOC 1 (Audit PHASE C)

**Si erreur :** Me donner :
1. Le message d'erreur exact
2. À quelle étape ça bloque
3. Les logs du backend (terminal où uvicorn tourne)

---

## 🔧 TROUBLESHOOTING

### Erreur "Module not found"
```powershell
# Vérifier que le venv est activé
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Erreur "Port 8001 already in use"
```powershell
# Trouver le processus
netstat -ano | findstr :8001
# Tuer le processus (remplacer PID)
taskkill /PID <PID> /F
```

### Erreur "Port 3000 already in use"
```powershell
# Trouver le processus
netstat -ano | findstr :3000
# Tuer le processus
taskkill /PID <PID> /F
```

### Backend démarre mais frontend ne peut pas se connecter
- Vérifier que le backend écoute sur `0.0.0.0` (pas `127.0.0.1`)
- Vérifier le firewall Windows
- Vérifier que `CORS_ORIGINS` dans .env inclut `http://localhost:3000` ou `*`

### Backtest échoue avec "Data file not found"
- Vérifier que `data/historical/1m/SPY.parquet` existe
- Vérifier les dates : utiliser une date où vous avez des données
- Vérifier le path_resolver : `python backend\utils\path_resolver.py`

---

**FIN BLOC 0**


