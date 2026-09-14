# Lendistry PD Demo

Modern **FastAPI + custom web UI** for Lendistry Probability of Default — underwriter workspace and admin model lab.

(Streamlit `app.py` remains as a legacy option; preferred UI is the new web app.)

## Run the new UI

```bash
cd "c:\Users\Purnesh.Guptha\Desktop\Lendistry Loan\pd_demo"
pip install -r requirements.txt
python generate_data.py
python train.py
python business_data.py
uvicorn server:app --host 0.0.0.0 --port 8501
```

Open [http://localhost:8501](http://localhost:8501)

## Roles

| Role | Screens |
|------|---------|
| **Underwriter** | Home · Application dashboard · Business insights |
| **Admin** | Overview · Model performance · Feature importance · Sandbox score |

## NSSM

| Field | Value |
|-------|--------|
| **Path** | `C:\Users\Purnesh.Guptha\AppData\Local\Programs\Python\Python311\python.exe` |
| **Startup directory** | `C:\Users\Purnesh.Guptha\Desktop\Lendistry Loan\pd_demo` |
| **Arguments** | `-m uvicorn server:app --host 0.0.0.0 --port 8501` |

Restart the NSSM service after changing Path/Arguments so it leaves Streamlit.

## Project layout

```
pd_demo/
├── server.py           # FastAPI API + static UI
├── static/             # HTML / CSS / JS frontend
├── business_data.py    # Applications + weekly insights
├── generate_data.py
├── train.py
├── config.py
├── app.py              # Legacy Streamlit (optional)
└── artifacts/
```

## Notes

- Synthetic demo data; Charged-Off proxy for default.
- Leakage-safe features only (no status/DPD).
- Best model: Gradient Boosting (75/25 split).
