# Hackathon Live Demo Test Scenarios

These scripts test Code-Mix handling, voice corrections, and danger-sign escalation.

---

## Scenario 1: Standard ANC Visit with Voice Correction
**Spoken Input (Code-mixed Hindi + English):**
> "ASHA worker Sunita here. Beneficiary ID 1042, Sunita Devi ka 3rd ANC checkup kiya. Weight 52 kilo hai. TT injection de diya, aur 30 din ki IFA goli dedi. Next visit 25 November ko karni hai."

**Expected Agent Read-back:**
> "Sunita ji, maine note kiya: Beneficiary ID 1042, ANC checkup, wazan 52 kilo, TT injection diya gaya, aur agla visit 25 November. Kya yeh theek hai?"

**ASHA Worker Spoken Correction:**
> "Nahi, agla visit 28 November ko hai."

**Expected Agent Confirmation:**
> "Samajh gaya. Agla visit 28 November update kar diya hai. Record save ho gaya."

---

## Scenario 2: Newborn Danger Sign Escalation (High Fever)
**Spoken Input (Code-mixed Hindi + English):**
> "Beneficiary ID 2088, newborn home visit. Baby ka wazan 2.6 kilo hai, par baby ko tez bukhar hai aur doodh nahi pi raha."

**Expected Agent Escalation (Urgent Alert):**
> "Chetavani: Baby ko tez bukhar aur feed na lene ke lakshan MoHFW danger list me hain. Kripya beneficiary ko turant nazdiki PHC refer karein! Record flag kar diya gaya hai."

---

## Scenario 3: Pregnancy Danger Sign Escalation (Vaginal Bleeding)
**Spoken Input:**
> "Beneficiary ID 3012, 7th month pregnancy visit. Patient ko halka bleeding ho raha hai aur sar dard hai."

**Expected Agent Escalation (Immediate Referral):**
> "Savdhaan: Bleeding aur sar dard gambhir sanket hain. Mareez ko tatkaal PHC le jayein. Record emergency flag ke sath darj kiya gaya hai."
