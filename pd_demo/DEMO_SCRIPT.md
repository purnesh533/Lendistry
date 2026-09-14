# Demo script (Megha — business-first)

## Start
```bash
cd "c:\Users\Purnesh.Guptha\Desktop\Lendistry Loan\pd_demo"
uvicorn server:app --host 0.0.0.0 --port 8501
```
Open http://localhost:8501

## 1. Login as Underwriter
> “Same model underneath — this view is for underwriters, not data scientists.”

**Home** — KPIs + **Portfolio pulse** (this week vs last week). Point at the disclaimer banner.

## 2. Application dashboard
Filter **Risky**, open one application popup.
Watch **Agent 1 → Agent 2 → Agent 3**, then **Final outcome** reveals.
Show: **default risk score**, plain-English “1 in N”, why flagged.
Click **Refer** (or Approve/Decline). Optional: **Replay agents**.
**Copy summary** for credit-committee story.

## 3. Business insights
Weekly mix + outcome table (manager view) + business driver cards (not model %).

## 4. Switch role → Admin (sidebar button)
Model performance (AUC), feature importance %, sandbox with Advanced collapsed.

## Close
> “Synthetic demo · Charged-Off proxy · happy to refine before Monday.”
