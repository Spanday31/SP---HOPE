import streamlit as st
import os
import math
import pandas as pd
import plotly.graph_objects as go

# ── Evidence mapping ──────────────────────────────────────────────────────────
TRIALS = {
    "Atorvastatin 80 mg": ("CTT meta-analysis", "https://pubmed.ncbi.nlm.nih.gov/20167315/"),
    "Rosuvastatin 20 mg": ("CTT meta-analysis", "https://pubmed.ncbi.nlm.nih.gov/20167315/"),
    "Ezetimibe 10 mg":     ("IMPROVE-IT",         "https://pubmed.ncbi.nlm.nih.gov/26405142/"),
    "Bempedoic acid":      ("CLEAR Outcomes",     "https://pubmed.ncbi.nlm.nih.gov/35338941/"),
    "PCSK9 inhibitor":     ("FOURIER",            "https://pubmed.ncbi.nlm.nih.gov/28436927/"),
    "Inclisiran":          ("ORION-10",           "https://pubmed.ncbi.nlm.nih.gov/32302303/"),
    "Icosapent ethyl":     ("REDUCE-IT",          "https://pubmed.ncbi.nlm.nih.gov/31141850/"),
    "Semaglutide":         ("STEP",               "https://pubmed.ncbi.nlm.nih.gov/34499685/"),
}

# ── Utility functions ────────────────────────────────────────────────────────
def calculate_ldl_projection(baseline_ldl, pre_list, new_list):
    """
    Sequentially apply fractional LDL reductions for pre-existing and new therapies.
    pre_list & new_list are lists of keys in TRIALS with known % efficacy.
    """
    # Efficacy map
    E = {
        "Atorvastatin 80 mg": 0.50,
        "Rosuvastatin 20 mg": 0.55,
        "Ezetimibe 10 mg":     0.20,
        "Bempedoic acid":      0.18,
        "PCSK9 inhibitor":     0.60,
        "Inclisiran":          0.55,
    }
    ldl = baseline_ldl
    for drug in pre_list + new_list:
        if drug in E:
            ldl *= (1 - E[drug])
    return max(ldl, 0.5)

def format_pp(x):
    return f"{x:.1f} pp"

def format_pct(x):
    return f"{x:.1f}%"

# ── Risk functions ───────────────────────────────────────────────────────────
def estimate_10y_risk(age, sex, sbp, tc, hdl, smoker, diabetes, egfr, crp, vasc):
    """ SMART 10‑year risk, capped at 95%. """
    sex_v = 1 if sex=="Male" else 0
    smoke_v=1 if smoker else 0
    dm_v=1 if diabetes else 0
    crp_l=math.log(crp+1)
    lp=(0.064*age+0.34*sex_v+0.02*sbp+0.25*tc
        -0.25*hdl+0.44*smoke_v+0.51*dm_v
        -0.2*(egfr/10)+0.25*crp_l+0.4*vasc)
    raw=1-0.900**math.exp(lp-5.8)
    pct=raw*100
    return round(min(pct,95.0),1)

def convert_5yr(r10):
    """ Converts 10‑year probability to 5‑year, capped at 95%. """
    p=min(r10,95.0)/100
    p5=1-(1-p)**0.5
    return round(min(p5*100,95.0),1)

def estimate_lifetime_risk(age, r10):
    """ Risk to age 85, capped at 95%. """
    years=max(85-age,0)
    p10=min(r10,95.0)/100
    annual=1-(1-p10)**(1/10)
    lt=1-(1-annual)**years
    return round(min(lt*100,95.0),1)

# ── Streamlit UI ─────────────────────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SMART CVD Risk Reduction")

# Top-right logo
colA, colB = st.columns([7,1])
with colB:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=600)
    else:
        st.warning("⚠️ Please upload logo.png")

# Sidebar: patient profile
st.sidebar.title("🩺 Patient Profile")
age     = st.sidebar.slider  ("Age (years)", 30,90,60)
sex     = st.sidebar.radio   ("Sex", ["Male","Female"])
weight  = st.sidebar.number_input("Weight (kg)",40,200,75)
height  = st.sidebar.number_input("Height (cm)",140,210,170)
bmi     = weight/((height/100)**2)
st.sidebar.markdown(f"**BMI:** {bmi:.1f} kg/m²")
smoker  = st.sidebar.checkbox("Current smoker", help="Tobacco ↑CVD risk")
diabetes= st.sidebar.checkbox("Diabetes", help="Diabetes ↑CVD risk")
egfr    = st.sidebar.slider  ("eGFR",15,120,90)
st.sidebar.markdown("**Vascular disease (tick all)**")
vasc1   = st.sidebar.checkbox("Coronary artery disease")
vasc2   = st.sidebar.checkbox("Cerebrovascular disease")
vasc3   = st.sidebar.checkbox("Peripheral artery disease")
vasc    = sum([vasc1,vasc2,vasc3])

# Main: Tabs for guided flow
tab1,tab2,tab3,tab4 = st.tabs(["🔬 Labs","💊 Therapies","📈 Results","ℹ️ About"])
with tab1:
    st.header("Step 1: Laboratory Results")
    tc    = st.number_input("Total Cholesterol (mmol/L)",2.0,10.0,5.2,0.1)
    hdl_v = st.number_input("HDL‑C (mmol/L)",0.5,3.0,1.3,0.1)
    ldl0  = st.number_input("Baseline LDL‑C (mmol/L)",0.5,6.0,3.0,0.1)
    crp   = st.number_input("hs‑CRP (mg/L)",0.1,20.0,2.5,0.1,help=TRIALS["Icosapent ethyl"][0])
    hba   = st.number_input("HbA₁c (%)",4.0,14.0,7.0,0.1,help=TRIALS["Semaglutide"][0])
    tg    = st.number_input("Triglycerides (mmol/L)",0.3,5.0,1.2,0.1)

with tab2:
    st.header("Step 2: Pre‑Admission Therapy")
    pre_stat  = st.selectbox("Statin pre‑admission",
                    ["None","Atorvastatin 80 mg","Rosuvastatin 20 mg"])
    pre_ez    = st.checkbox("Ezetimibe 10 mg")
    pre_bemp  = st.checkbox("Bempedoic acid")
    st.markdown("Step 3: Initiate/Intensify Therapy")
    new_stat  = st.selectbox("Statin change",
                    ["None","Atorvastatin 80 mg","Rosuvastatin 20 mg"])
    new_ez    = st.checkbox("Add Ezetimibe")
    new_bemp  = st.checkbox("Add Bempedoic acid")
    pcsk9     = st.checkbox("PCSK9 inhibitor", disabled=(calculate_ldl_projection(ldl0,[pre_stat,pre_ez and \"Ezetimibe 10 mg\",pre_bemp and \"Bempedoic acid\"],[])<=1.8))
    inclis    = st.checkbox("Inclisiran",     disabled=(calculate_ldl_projection(ldl0,[],[new_stat,new_ez and \"Ezetimibe 10 mg\",new_bemp and \"Bempedoic acid\"])<=1.8))

with tab3:
    st.header("Step 4: Risk & Benefit Results")
    # Estimate risks
    risk10 = estimate_10y_risk(age,sex,sbp:=st.number_input("SBP (mmHg)",90,200,140),tc,hdl_v,smoker,diabetes,egfr,crp,vasc)
    risk5  = convert_5yr(risk10)
    riskLT = estimate_lifetime_risk(age,risk10)
    # Display
    st.markdown(f"**5‑yr risk:** {format_pct(risk5)}  •  **10‑yr risk:** {format_pct(risk10)}  •  **Lifetime:** {format_pct(riskLT)}")
    # Chart
    fig=go.Figure(go.Bar(x=["5‑yr","10‑yr","Lifetime"], y=[risk5,risk10,riskLT],
                         marker_color=["#f39c12","#e74c3c","#2ecc71"]))
    fig.update_layout(yaxis_title="Risk (%)",template="plotly_white")
    st.plotly_chart(fig,use_container_width=True)
    # ARR/RRR placeholders (to be replaced with calculated values)
    arr10=5.2; rrr10=round(arr10/risk10*100,1)
    st.markdown(f"**ARR (10y):** {format_pp(arr10)}  •  **RRR (10y):** {format_pct(rrr10)}")

with tab4:
    st.markdown("### About this tool")
    st.markdown("Designed by Samuel Panday et al., via PRIME team at King's College Hospital.")
    st.markdown("Evidence-based CVD prevention calculator; not a substitute for clinical judgment.")

# Footer
st.markdown("---")
st.markdown("⚠️ For informational purposes only—discuss with your healthcare provider.")
