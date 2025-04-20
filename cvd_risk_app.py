
import streamlit as st
import math
import matplotlib.pyplot as plt

# ----- Intervention data -----
interventions = [
    {"name": "Smoking cessation", "arr_lifetime": 17, "arr_5yr": 5},
    {"name": "Antiplatelet (ASA or clopidogrel)", "arr_lifetime": 6, "arr_5yr": 2},
    {"name": "BP control (ACEi/ARB ± CCB)", "arr_lifetime": 12, "arr_5yr": 4},
    {"name": "Semaglutide 2.4 mg", "arr_lifetime": 4, "arr_5yr": 1},
    {"name": "Weight loss to ideal BMI", "arr_lifetime": 10, "arr_5yr": 3},
    {"name": "Empagliflozin", "arr_lifetime": 6, "arr_5yr": 2},
    {"name": "Icosapent ethyl (TG ≥1.5)", "arr_lifetime": 5, "arr_5yr": 2},
    {"name": "Mediterranean diet", "arr_lifetime": 9, "arr_5yr": 3},
    {"name": "Physical activity", "arr_lifetime": 9, "arr_5yr": 3},
    {"name": "Alcohol moderation", "arr_lifetime": 5, "arr_5yr": 2},
    {"name": "Stress reduction", "arr_lifetime": 3, "arr_5yr": 1}
]

ldl_therapies = {
    "Atorvastatin 20 mg": 40,
    "Atorvastatin 80 mg": 50,
    "Rosuvastatin 10 mg": 40,
    "Rosuvastatin 20-40 mg": 55,
    "Simvastatin 40 mg": 35,
    "Ezetimibe": 20,
    "PCSK9 inhibitor": 60,
    "Bempedoic acid": 18
}

# ----- SMART Risk Score functions -----
def estimate_smart_risk(age, sex, sbp, total_chol, hdl, smoker, diabetes, egfr, crp, vasc_count):
    sex_val = 1 if sex == "Male" else 0
    smoking_val = 1 if smoker else 0
    diabetes_val = 1 if diabetes else 0
    crp_log = math.log(crp + 1) if crp else 0
    lp = (0.064*age + 0.34*sex_val + 0.02*sbp + 0.25*total_chol -
          0.25*hdl + 0.44*smoking_val + 0.51*diabetes_val -
          0.2*(egfr/10) + 0.25*crp_log + 0.4*vasc_count)
    risk10 = 1 - 0.900**math.exp(lp - 5.8)
    return round(risk10 * 100, 1)

def estimate_5yr_from_10yr(risk10):
    p = risk10 / 100
    risk5 = 1 - (1-p)**0.5
    return round(risk5 * 100, 1)

# ----- App UI -----
st.title("Comprehensive SMART CVD Risk Reduction Calculator")

patient_mode = st.checkbox("Patient-friendly view")
horizon = st.radio("Select time horizon", ["5yr", "10yr", "lifetime"], index=1)

if not patient_mode:
    st.subheader("Patient Baseline Characteristics")
    age = st.slider("Age", 30, 90, 60)
    sex = st.radio("Sex", ["Male", "Female"])
    smoker = st.checkbox("Currently smoking")
    diabetes = st.checkbox("Diabetes")
    egfr = st.slider("eGFR (mL/min/1.73 m²)", 15, 120, 80)
    total_chol = st.number_input("Total Cholesterol (mmol/L)", 2.0, 10.0, 5.0, 0.1)
    hdl = st.number_input("HDL-C (mmol/L)", 0.5, 3.0, 1.0, 0.1)
    crp = st.number_input("hs-CRP (mg/L) [Not during acute MI]", 0.1, 20.0, 2.0, 0.1)
    if crp > 10:
        st.warning("hs-CRP >10 mg/L suggests acute inflammation.")
    st.markdown("### Vascular Disease History")
    vasc = ["Coronary artery disease", "Cerebrovascular disease", "Peripheral artery disease"]
    vasc_count = sum([st.checkbox(v) for v in vasc])

    st.subheader("Blood Pressure")
    sbp_current = st.number_input("Current SBP (mmHg)", 80, 220, 145)
    sbp_target = st.number_input("Target SBP (mmHg)", 80, 220, 120)
    if sbp_target >= sbp_current:
        st.warning("Target SBP should be lower than current SBP.")

    st.subheader("Lipid-lowering Therapy")
    baseline_ldl = st.number_input("Baseline LDL-C (mmol/L)", 0.5, 6.0, 3.5, 0.1)
    st.markdown("#### Already on therapy (select all that apply)")
    on_therapy = [d for d in ldl_therapies if st.checkbox(d)]
    adjusted_ldl = baseline_ldl
    for d in on_therapy:
        adjusted_ldl *= (1 - ldl_therapies[d]/100)
    adjusted_ldl = max(adjusted_ldl, 1.0)

    st.markdown("#### Add or intensify therapy now")
    additional = [d for d in ldl_therapies if d not in on_therapy and st.checkbox(d + " (new)")]
    final_ldl = adjusted_ldl
    for d in additional:
        final_ldl *= (1 - (ldl_therapies[d]/100)*0.5)
    final_ldl = max(final_ldl, 1.0)

    st.markdown("### Other Interventions")
    selected_iv = st.multiselect("Select interventions", [iv["name"] for iv in interventions])

else:
    st.subheader("Patient-friendly Inputs")
    age = st.slider("Age", 30, 90, 60)
    sbp_current = st.number_input("Current SBP (mmHg)", 80, 220, 145)
    sbp_target = st.number_input("Target SBP (mmHg)", 80, 220, 120)
    total_chol = st.number_input("Total Cholesterol (mmol/L)", 2.0, 10.0, 5.0, 0.1)
    baseline_ldl = st.number_input("Baseline LDL-C (mmol/L)", 0.5, 6.0, 3.5, 0.1)
    final_ldl = st.number_input("Expected LDL-C after therapy (estimated)", 0.5, 6.0, 2.0, 0.1)
    selected_iv = []; vasc_count = 1; smoker=False; diabetes=False; egfr=80; hdl=1.0; crp=2.0; on_therapy=[]

risk10 = estimate_smart_risk(age, sex, sbp_current, total_chol, hdl, smoker, diabetes, egfr, crp, vasc_count)
risk5 = estimate_5yr_from_10yr(risk10)
baseline_risk = risk5 if horizon=="5yr" else risk10

remaining = baseline_risk/100
for iv in interventions:
    if iv["name"] in selected_iv:
        arr = iv["arr_5yr"] if horizon=="5yr" else iv["arr_lifetime"]
        remaining *= (1 - arr/100)

ldl_drop = baseline_ldl - final_ldl
ldl_rrr = min(22*ldl_drop, 35)
remaining *= (1 - ldl_rrr/100)

bp_rrr = min(15*((sbp_current - sbp_target)/10), 20)
remaining *= (1 - bp_rrr/100)

final_risk = round(remaining*100,1)
arr = round(baseline_risk - final_risk,1)
rrr = round(arr/baseline_risk*100,1) if baseline_risk else 0

if st.button("Calculate"):
    st.write(f"Baseline {horizon} risk: {baseline_risk}%")
    st.write(f"Final risk: {final_risk}% (ARR: {arr} pp, RRR: {rrr}% )")

if st.button("Show Chart"):
    fig, ax = plt.subplots()
    ax.bar(["Baseline","After"], [baseline_risk, final_risk], color=["#CC4444","#44CC44"], alpha=0.9)
    ax.set_ylabel(f"{horizon} risk (%)")
    st.pyplot(fig)
