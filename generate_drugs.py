"""
MedMind Drug Database Generator — добавляет 600+ препаратов через Groq API.

Генерирует полные клинические профили: механизм, показания, дозирование,
побочные эффекты, мониторинг, предупреждения о чёрном ящике.

После генерации автоматически запускает:
  - fetch_drug_images.py (Wikipedia фото)
  - translate_drugs.py (6 языков)

Usage:
    python3 generate_drugs.py --limit 100
    python3 generate_drugs.py --class cardiovascular
    python3 generate_drugs.py --dry-run   # показать список без генерации

Run in background:
    nohup python3 generate_drugs.py --limit 2000 > /tmp/gen_drugs.log 2>&1 &
"""
import argparse
import json
import logging
import os
import re
import sys
import time
import uuid

import httpx
import psycopg2

sys.path.insert(0, os.path.dirname(__file__))
from generate_articles_ollama import DB_URL

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

# ── Comprehensive drug list by class ─────────────────────────────────────────

DRUG_LIST: dict[str, list[tuple[str, str]]] = {
    # (generic_name, drug_class)
    "cardiovascular": [
        ("Metoprolol Succinate", "Beta-1 Selective Blocker"),
        ("Metoprolol Tartrate", "Beta-1 Selective Blocker"),
        ("Carvedilol", "Non-selective Beta Blocker"),
        ("Bisoprolol", "Beta-1 Selective Blocker"),
        ("Propranolol", "Non-selective Beta Blocker"),
        ("Nebivolol", "Beta-1 Selective Blocker"),
        ("Labetalol", "Alpha and Beta Blocker"),
        ("Sotalol", "Class III Antiarrhythmic"),
        ("Lisinopril", "ACE Inhibitor"),
        ("Enalapril", "ACE Inhibitor"),
        ("Ramipril", "ACE Inhibitor"),
        ("Captopril", "ACE Inhibitor"),
        ("Perindopril", "ACE Inhibitor"),
        ("Quinapril", "ACE Inhibitor"),
        ("Fosinopril", "ACE Inhibitor"),
        ("Trandolapril", "ACE Inhibitor"),
        ("Losartan", "Angiotensin Receptor Blocker"),
        ("Valsartan", "Angiotensin Receptor Blocker"),
        ("Irbesartan", "Angiotensin Receptor Blocker"),
        ("Candesartan", "Angiotensin Receptor Blocker"),
        ("Olmesartan", "Angiotensin Receptor Blocker"),
        ("Telmisartan", "Angiotensin Receptor Blocker"),
        ("Azilsartan", "Angiotensin Receptor Blocker"),
        ("Sacubitril-Valsartan", "Angiotensin Receptor-Neprilysin Inhibitor"),
        ("Amlodipine", "Calcium Channel Blocker"),
        ("Nifedipine", "Dihydropyridine Calcium Channel Blocker"),
        ("Diltiazem", "Non-dihydropyridine Calcium Channel Blocker"),
        ("Verapamil", "Non-dihydropyridine Calcium Channel Blocker"),
        ("Felodipine", "Dihydropyridine Calcium Channel Blocker"),
        ("Nicardipine", "Dihydropyridine Calcium Channel Blocker"),
        ("Clevidipine", "Dihydropyridine Calcium Channel Blocker"),
        ("Atorvastatin", "HMG-CoA Reductase Inhibitor"),
        ("Rosuvastatin", "HMG-CoA Reductase Inhibitor"),
        ("Simvastatin", "HMG-CoA Reductase Inhibitor"),
        ("Pravastatin", "HMG-CoA Reductase Inhibitor"),
        ("Lovastatin", "HMG-CoA Reductase Inhibitor"),
        ("Fluvastatin", "HMG-CoA Reductase Inhibitor"),
        ("Pitavastatin", "HMG-CoA Reductase Inhibitor"),
        ("Ezetimibe", "Cholesterol Absorption Inhibitor"),
        ("Evolocumab", "PCSK9 Inhibitor"),
        ("Alirocumab", "PCSK9 Inhibitor"),
        ("Inclisiran", "PCSK9 siRNA"),
        ("Furosemide", "Loop Diuretic"),
        ("Bumetanide", "Loop Diuretic"),
        ("Torsemide", "Loop Diuretic"),
        ("Ethacrynic Acid", "Loop Diuretic"),
        ("Hydrochlorothiazide", "Thiazide Diuretic"),
        ("Chlorthalidone", "Thiazide-like Diuretic"),
        ("Indapamide", "Thiazide-like Diuretic"),
        ("Metolazone", "Thiazide-like Diuretic"),
        ("Spironolactone", "Aldosterone Antagonist"),
        ("Eplerenone", "Aldosterone Antagonist"),
        ("Finerenone", "Non-steroidal Mineralocorticoid Receptor Antagonist"),
        ("Triamterene", "Potassium-sparing Diuretic"),
        ("Amiloride", "Potassium-sparing Diuretic"),
        ("Digoxin", "Cardiac Glycoside"),
        ("Amiodarone", "Class III Antiarrhythmic"),
        ("Dronedarone", "Class III Antiarrhythmic"),
        ("Flecainide", "Class IC Antiarrhythmic"),
        ("Propafenone", "Class IC Antiarrhythmic"),
        ("Dofetilide", "Class III Antiarrhythmic"),
        ("Ivabradine", "If Channel Blocker"),
        ("Ranolazine", "Late Sodium Channel Blocker"),
        ("Hydralazine", "Direct Vasodilator"),
        ("Minoxidil", "Direct Vasodilator"),
        ("Isosorbide Mononitrate", "Organic Nitrate"),
        ("Isosorbide Dinitrate", "Organic Nitrate"),
        ("Nitroglycerin", "Organic Nitrate"),
        ("Nitroprusside", "Direct Vasodilator"),
        ("Bosentan", "Endothelin Receptor Antagonist"),
        ("Ambrisentan", "Endothelin Receptor Antagonist"),
        ("Macitentan", "Endothelin Receptor Antagonist"),
        ("Sildenafil", "PDE5 Inhibitor"),
        ("Tadalafil", "PDE5 Inhibitor"),
        ("Riociguat", "Soluble Guanylate Cyclase Stimulator"),
        ("Warfarin", "Vitamin K Antagonist"),
        ("Rivaroxaban", "Factor Xa Inhibitor"),
        ("Apixaban", "Factor Xa Inhibitor"),
        ("Edoxaban", "Factor Xa Inhibitor"),
        ("Betrixaban", "Factor Xa Inhibitor"),
        ("Dabigatran", "Direct Thrombin Inhibitor"),
        ("Heparin", "Indirect Thrombin Inhibitor"),
        ("Enoxaparin", "Low Molecular Weight Heparin"),
        ("Dalteparin", "Low Molecular Weight Heparin"),
        ("Fondaparinux", "Factor Xa Inhibitor"),
        ("Argatroban", "Direct Thrombin Inhibitor"),
        ("Bivalirudin", "Direct Thrombin Inhibitor"),
        ("Aspirin", "Antiplatelet / COX Inhibitor"),
        ("Clopidogrel", "P2Y12 Receptor Antagonist"),
        ("Ticagrelor", "P2Y12 Receptor Antagonist"),
        ("Prasugrel", "P2Y12 Receptor Antagonist"),
        ("Cangrelor", "P2Y12 Receptor Antagonist"),
        ("Eptifibatide", "GPIIb/IIIa Inhibitor"),
        ("Tirofiban", "GPIIb/IIIa Inhibitor"),
        ("Vorapaxar", "PAR-1 Antagonist"),
        ("Alteplase", "Thrombolytic"),
        ("Tenecteplase", "Thrombolytic"),
        ("Reteplase", "Thrombolytic"),
        ("Dapagliflozin", "SGLT2 Inhibitor"),
        ("Empagliflozin", "SGLT2 Inhibitor"),
        ("Sotagliflozin", "SGLT1/2 Inhibitor"),
        ("Colchicine", "Anti-inflammatory"),
        ("Fenofibrate", "Fibric Acid Derivative"),
        ("Gemfibrozil", "Fibric Acid Derivative"),
        ("Niacin", "Nicotinic Acid"),
        ("Omega-3 Fatty Acids", "Lipid-lowering Agent"),
    ],

    "antibiotics": [
        ("Amoxicillin", "Aminopenicillin"),
        ("Amoxicillin-Clavulanate", "Beta-lactam / Beta-lactamase Inhibitor"),
        ("Ampicillin", "Aminopenicillin"),
        ("Ampicillin-Sulbactam", "Beta-lactam / Beta-lactamase Inhibitor"),
        ("Piperacillin-Tazobactam", "Antipseudomonal Penicillin / Beta-lactamase Inhibitor"),
        ("Nafcillin", "Antistaphylococcal Penicillin"),
        ("Oxacillin", "Antistaphylococcal Penicillin"),
        ("Dicloxacillin", "Antistaphylococcal Penicillin"),
        ("Cephalexin", "First Generation Cephalosporin"),
        ("Cefazolin", "First Generation Cephalosporin"),
        ("Cefadroxil", "First Generation Cephalosporin"),
        ("Cefuroxime", "Second Generation Cephalosporin"),
        ("Cefprozil", "Second Generation Cephalosporin"),
        ("Cefaclor", "Second Generation Cephalosporin"),
        ("Ceftriaxone", "Third Generation Cephalosporin"),
        ("Cefotaxime", "Third Generation Cephalosporin"),
        ("Cefdinir", "Third Generation Cephalosporin"),
        ("Cefixime", "Third Generation Cephalosporin"),
        ("Cefpodoxime", "Third Generation Cephalosporin"),
        ("Ceftazidime", "Third Generation Antipseudomonal Cephalosporin"),
        ("Cefepime", "Fourth Generation Cephalosporin"),
        ("Ceftaroline", "Fifth Generation Cephalosporin / Anti-MRSA"),
        ("Ceftazidime-Avibactam", "Beta-lactam / Beta-lactamase Inhibitor Combination"),
        ("Ceftolozane-Tazobactam", "Beta-lactam / Beta-lactamase Inhibitor Combination"),
        ("Cefiderocol", "Siderophore Cephalosporin"),
        ("Imipenem-Cilastatin", "Carbapenem"),
        ("Meropenem", "Carbapenem"),
        ("Ertapenem", "Carbapenem"),
        ("Doripenem", "Carbapenem"),
        ("Meropenem-Vaborbactam", "Carbapenem / Beta-lactamase Inhibitor"),
        ("Imipenem-Relebactam", "Carbapenem / Beta-lactamase Inhibitor"),
        ("Aztreonam", "Monobactam"),
        ("Doxycycline", "Tetracycline"),
        ("Minocycline", "Tetracycline"),
        ("Tetracycline", "Tetracycline"),
        ("Omadacycline", "Aminomethylcycline Tetracycline"),
        ("Eravacycline", "Fluorocycline Tetracycline"),
        ("Tigecycline", "Glycylcycline Tetracycline"),
        ("Azithromycin", "Macrolide"),
        ("Clarithromycin", "Macrolide"),
        ("Erythromycin", "Macrolide"),
        ("Fidaxomicin", "Macrolide"),
        ("Ciprofloxacin", "Fluoroquinolone"),
        ("Levofloxacin", "Fluoroquinolone"),
        ("Moxifloxacin", "Fluoroquinolone"),
        ("Ofloxacin", "Fluoroquinolone"),
        ("Delafloxacin", "Fluoroquinolone"),
        ("Trimethoprim-Sulfamethoxazole", "Sulfonamide Combination"),
        ("Clindamycin", "Lincosamide"),
        ("Vancomycin", "Glycopeptide"),
        ("Telavancin", "Lipoglycopeptide"),
        ("Oritavancin", "Lipoglycopeptide"),
        ("Dalbavancin", "Lipoglycopeptide"),
        ("Linezolid", "Oxazolidinone"),
        ("Tedizolid", "Oxazolidinone"),
        ("Daptomycin", "Lipopeptide"),
        ("Gentamicin", "Aminoglycoside"),
        ("Tobramycin", "Aminoglycoside"),
        ("Amikacin", "Aminoglycoside"),
        ("Streptomycin", "Aminoglycoside"),
        ("Metronidazole", "Nitroimidazole"),
        ("Nitrofurantoin", "Nitrofuran"),
        ("Fosfomycin", "Phosphonic Acid Antibiotic"),
        ("Rifampin", "Rifamycin"),
        ("Rifabutin", "Rifamycin"),
        ("Rifaximin", "Rifamycin"),
        ("Colistin", "Polymyxin"),
        ("Polymyxin B", "Polymyxin"),
        ("Chloramphenicol", "Phenicol"),
        ("Cefazolin", "First Generation Cephalosporin"),
        ("Isoniazid", "Antitubercular"),
        ("Pyrazinamide", "Antitubercular"),
        ("Ethambutol", "Antitubercular"),
        ("Bedaquiline", "ATP Synthase Inhibitor / Antitubercular"),
        ("Delamanid", "Nitroimidazole / Antitubercular"),
        ("Pretomanid", "Nitroimidazole / Antitubercular"),
    ],

    "antifungals_antivirals": [
        ("Fluconazole", "Azole Antifungal"),
        ("Itraconazole", "Azole Antifungal"),
        ("Voriconazole", "Azole Antifungal"),
        ("Posaconazole", "Azole Antifungal"),
        ("Isavuconazole", "Azole Antifungal"),
        ("Micafungin", "Echinocandin Antifungal"),
        ("Caspofungin", "Echinocandin Antifungal"),
        ("Anidulafungin", "Echinocandin Antifungal"),
        ("Amphotericin B Liposomal", "Polyene Antifungal"),
        ("Flucytosine", "Pyrimidine Antifungal"),
        ("Terbinafine", "Allylamine Antifungal"),
        ("Griseofulvin", "Antifungal"),
        ("Acyclovir", "Nucleoside Analogue Antiviral"),
        ("Valacyclovir", "Nucleoside Analogue Antiviral"),
        ("Famciclovir", "Nucleoside Analogue Antiviral"),
        ("Ganciclovir", "Nucleoside Analogue Antiviral"),
        ("Valganciclovir", "Nucleoside Analogue Antiviral"),
        ("Foscarnet", "Pyrophosphate Analogue Antiviral"),
        ("Cidofovir", "Nucleotide Analogue Antiviral"),
        ("Letermovir", "CMV Terminase Inhibitor"),
        ("Maribavir", "UL97 Kinase Inhibitor"),
        ("Oseltamivir", "Neuraminidase Inhibitor"),
        ("Zanamivir", "Neuraminidase Inhibitor"),
        ("Baloxavir", "Cap-dependent Endonuclease Inhibitor"),
        ("Peramivir", "Neuraminidase Inhibitor"),
        ("Remdesivir", "RNA Polymerase Inhibitor"),
        ("Nirmatrelvir-Ritonavir", "SARS-CoV-2 Protease Inhibitor"),
        ("Molnupiravir", "RNA Polymerase Inhibitor"),
        ("Tenofovir Disoproxil Fumarate", "Nucleotide Reverse Transcriptase Inhibitor"),
        ("Tenofovir Alafenamide", "Nucleotide Reverse Transcriptase Inhibitor"),
        ("Emtricitabine", "Nucleoside Reverse Transcriptase Inhibitor"),
        ("Lamivudine", "Nucleoside Reverse Transcriptase Inhibitor"),
        ("Abacavir", "Nucleoside Reverse Transcriptase Inhibitor"),
        ("Efavirenz", "Non-nucleoside Reverse Transcriptase Inhibitor"),
        ("Rilpivirine", "Non-nucleoside Reverse Transcriptase Inhibitor"),
        ("Doravirine", "Non-nucleoside Reverse Transcriptase Inhibitor"),
        ("Dolutegravir", "HIV Integrase Inhibitor"),
        ("Bictegravir", "HIV Integrase Inhibitor"),
        ("Raltegravir", "HIV Integrase Inhibitor"),
        ("Elvitegravir", "HIV Integrase Inhibitor"),
        ("Cabotegravir", "HIV Integrase Inhibitor"),
        ("Darunavir", "HIV Protease Inhibitor"),
        ("Atazanavir", "HIV Protease Inhibitor"),
        ("Lopinavir-Ritonavir", "HIV Protease Inhibitor"),
        ("Ritonavir", "HIV Protease Inhibitor"),
        ("Cobicistat", "CYP3A4 Inhibitor / Pharmacokinetic Booster"),
        ("Maraviroc", "CCR5 Antagonist"),
        ("Ibalizumab", "CD4 Receptor Antagonist"),
        ("Fostemsavir", "HIV Attachment Inhibitor"),
        ("Lenacapavir", "HIV Capsid Inhibitor"),
        ("Sofosbuvir", "HCV NS5B Polymerase Inhibitor"),
        ("Ledipasvir", "HCV NS5A Inhibitor"),
        ("Velpatasvir", "HCV NS5A Inhibitor"),
        ("Glecaprevir-Pibrentasvir", "HCV NS3/4A + NS5A Inhibitor"),
        ("Elbasvir-Grazoprevir", "HCV NS5A + NS3/4A Inhibitor"),
    ],

    "cns_psychiatry": [
        ("Sertraline", "Selective Serotonin Reuptake Inhibitor"),
        ("Fluoxetine", "Selective Serotonin Reuptake Inhibitor"),
        ("Escitalopram", "Selective Serotonin Reuptake Inhibitor"),
        ("Citalopram", "Selective Serotonin Reuptake Inhibitor"),
        ("Paroxetine", "Selective Serotonin Reuptake Inhibitor"),
        ("Fluvoxamine", "Selective Serotonin Reuptake Inhibitor"),
        ("Venlafaxine", "Serotonin-Norepinephrine Reuptake Inhibitor"),
        ("Desvenlafaxine", "Serotonin-Norepinephrine Reuptake Inhibitor"),
        ("Duloxetine", "Serotonin-Norepinephrine Reuptake Inhibitor"),
        ("Levomilnacipran", "Serotonin-Norepinephrine Reuptake Inhibitor"),
        ("Milnacipran", "Serotonin-Norepinephrine Reuptake Inhibitor"),
        ("Bupropion", "Norepinephrine-Dopamine Reuptake Inhibitor"),
        ("Mirtazapine", "NaSSA Antidepressant"),
        ("Trazodone", "Serotonin Antagonist and Reuptake Inhibitor"),
        ("Nefazodone", "Serotonin Antagonist and Reuptake Inhibitor"),
        ("Amitriptyline", "Tricyclic Antidepressant"),
        ("Nortriptyline", "Tricyclic Antidepressant"),
        ("Imipramine", "Tricyclic Antidepressant"),
        ("Desipramine", "Tricyclic Antidepressant"),
        ("Clomipramine", "Tricyclic Antidepressant"),
        ("Doxepin", "Tricyclic Antidepressant"),
        ("Phenelzine", "Monoamine Oxidase Inhibitor"),
        ("Tranylcypromine", "Monoamine Oxidase Inhibitor"),
        ("Selegiline", "MAO-B Inhibitor"),
        ("Vilazodone", "Serotonin Partial Agonist Reuptake Inhibitor"),
        ("Vortioxetine", "Multimodal Antidepressant"),
        ("Ketamine", "NMDA Receptor Antagonist"),
        ("Esketamine", "NMDA Receptor Antagonist"),
        ("Brexanolone", "GABA-A Modulator / Neurosteroid"),
        ("Zuranolone", "GABA-A Modulator / Neurosteroid"),
        ("Lithium", "Mood Stabilizer"),
        ("Valproate", "Anticonvulsant / Mood Stabilizer"),
        ("Lamotrigine", "Anticonvulsant / Mood Stabilizer"),
        ("Carbamazepine", "Anticonvulsant / Mood Stabilizer"),
        ("Oxcarbazepine", "Anticonvulsant / Mood Stabilizer"),
        ("Haloperidol", "First Generation Antipsychotic"),
        ("Chlorpromazine", "First Generation Antipsychotic"),
        ("Fluphenazine", "First Generation Antipsychotic"),
        ("Perphenazine", "First Generation Antipsychotic"),
        ("Thiothixene", "First Generation Antipsychotic"),
        ("Risperidone", "Second Generation Antipsychotic"),
        ("Olanzapine", "Second Generation Antipsychotic"),
        ("Quetiapine", "Second Generation Antipsychotic"),
        ("Aripiprazole", "Dopamine Partial Agonist Antipsychotic"),
        ("Ziprasidone", "Second Generation Antipsychotic"),
        ("Paliperidone", "Second Generation Antipsychotic"),
        ("Asenapine", "Second Generation Antipsychotic"),
        ("Iloperidone", "Second Generation Antipsychotic"),
        ("Lurasidone", "Second Generation Antipsychotic"),
        ("Cariprazine", "Dopamine Partial Agonist Antipsychotic"),
        ("Brexpiprazole", "Dopamine Partial Agonist Antipsychotic"),
        ("Clozapine", "Atypical Antipsychotic"),
        ("Lumateperone", "Second Generation Antipsychotic"),
        ("Pimavanserin", "Selective Serotonin Inverse Agonist"),
        ("Methylphenidate", "CNS Stimulant"),
        ("Amphetamine", "CNS Stimulant"),
        ("Lisdexamfetamine", "CNS Stimulant Prodrug"),
        ("Dextroamphetamine", "CNS Stimulant"),
        ("Atomoxetine", "Selective Norepinephrine Reuptake Inhibitor"),
        ("Viloxazine", "Selective Norepinephrine Reuptake Inhibitor"),
        ("Guanfacine", "Alpha-2A Adrenergic Agonist"),
        ("Clonidine", "Alpha-2 Adrenergic Agonist"),
        ("Diazepam", "Benzodiazepine"),
        ("Lorazepam", "Benzodiazepine"),
        ("Clonazepam", "Benzodiazepine"),
        ("Alprazolam", "Benzodiazepine"),
        ("Midazolam", "Benzodiazepine"),
        ("Temazepam", "Benzodiazepine"),
        ("Triazolam", "Benzodiazepine"),
        ("Chlordiazepoxide", "Benzodiazepine"),
        ("Zolpidem", "Non-benzodiazepine Hypnotic"),
        ("Eszopiclone", "Non-benzodiazepine Hypnotic"),
        ("Zaleplon", "Non-benzodiazepine Hypnotic"),
        ("Melatonin", "Melatonin Receptor Agonist"),
        ("Ramelteon", "Melatonin Receptor Agonist"),
        ("Suvorexant", "Orexin Receptor Antagonist"),
        ("Lemborexant", "Orexin Receptor Antagonist"),
        ("Buspirone", "Partial Serotonin Agonist / Anxiolytic"),
        ("Hydroxyzine", "Antihistamine / Anxiolytic"),
        ("Phenobarbital", "Barbiturate"),
        ("Levetiracetam", "Anticonvulsant"),
        ("Lacosamide", "Sodium Channel Blocker Anticonvulsant"),
        ("Topiramate", "Anticonvulsant"),
        ("Gabapentin", "Anticonvulsant / Analgesic"),
        ("Pregabalin", "Anticonvulsant / Analgesic"),
        ("Zonisamide", "Anticonvulsant"),
        ("Perampanel", "AMPA Receptor Antagonist"),
        ("Cenobamate", "Anticonvulsant"),
        ("Brivaracetam", "Anticonvulsant"),
        ("Fenfluramine", "Serotonin-releasing Agent / Anticonvulsant"),
        ("Levodopa-Carbidopa", "Dopamine Precursor / Decarboxylase Inhibitor"),
        ("Pramipexole", "Dopamine Agonist"),
        ("Ropinirole", "Dopamine Agonist"),
        ("Rotigotine", "Dopamine Agonist"),
        ("Rasagiline", "MAO-B Inhibitor"),
        ("Entacapone", "COMT Inhibitor"),
        ("Amantadine", "NMDA Antagonist / Dopaminergic"),
        ("Donepezil", "Acetylcholinesterase Inhibitor"),
        ("Rivastigmine", "Acetylcholinesterase Inhibitor"),
        ("Galantamine", "Acetylcholinesterase Inhibitor"),
        ("Memantine", "NMDA Receptor Antagonist"),
        ("Lecanemab", "Anti-Amyloid Monoclonal Antibody"),
        ("Donanemab", "Anti-Amyloid Monoclonal Antibody"),
        ("Sumatriptan", "Serotonin 5-HT1 Agonist / Triptan"),
        ("Rizatriptan", "Serotonin 5-HT1 Agonist / Triptan"),
        ("Eletriptan", "Serotonin 5-HT1 Agonist / Triptan"),
        ("Naratriptan", "Serotonin 5-HT1 Agonist / Triptan"),
        ("Almotriptan", "Serotonin 5-HT1 Agonist / Triptan"),
        ("Lasmiditan", "Serotonin 5-HT1F Agonist"),
        ("Ubrogepant", "CGRP Receptor Antagonist"),
        ("Rimegepant", "CGRP Receptor Antagonist"),
        ("Atogepant", "CGRP Receptor Antagonist"),
        ("Erenumab", "CGRP Receptor Monoclonal Antibody"),
        ("Fremanezumab", "CGRP Monoclonal Antibody"),
        ("Galcanezumab", "CGRP Monoclonal Antibody"),
        ("Eptinezumab", "CGRP Monoclonal Antibody"),
        ("Naltrexone", "Opioid Receptor Antagonist"),
        ("Naloxone", "Opioid Receptor Antagonist"),
        ("Buprenorphine", "Partial Opioid Agonist"),
        ("Buprenorphine-Naloxone", "Partial Opioid Agonist / Antagonist"),
        ("Methadone", "Full Opioid Agonist / NMDA Antagonist"),
        ("Disulfiram", "Aldehyde Dehydrogenase Inhibitor"),
        ("Acamprosate", "GABA Modulator / Glutamate Antagonist"),
        ("Varenicline", "Nicotinic Receptor Partial Agonist"),
        ("Nortriptyline", "Tricyclic Antidepressant"),
        ("Chlorpromazine", "First Generation Antipsychotic"),
    ],

    "endocrine": [
        ("Metformin", "Biguanide"),
        ("Glipizide", "Sulfonylurea"),
        ("Glyburide", "Sulfonylurea"),
        ("Glimepiride", "Sulfonylurea"),
        ("Pioglitazone", "Thiazolidinedione"),
        ("Rosiglitazone", "Thiazolidinedione"),
        ("Sitagliptin", "DPP-4 Inhibitor"),
        ("Saxagliptin", "DPP-4 Inhibitor"),
        ("Linagliptin", "DPP-4 Inhibitor"),
        ("Alogliptin", "DPP-4 Inhibitor"),
        ("Semaglutide", "GLP-1 Receptor Agonist"),
        ("Liraglutide", "GLP-1 Receptor Agonist"),
        ("Dulaglutide", "GLP-1 Receptor Agonist"),
        ("Exenatide", "GLP-1 Receptor Agonist"),
        ("Tirzepatide", "GLP-1/GIP Dual Receptor Agonist"),
        ("Dapagliflozin", "SGLT2 Inhibitor"),
        ("Empagliflozin", "SGLT2 Inhibitor"),
        ("Canagliflozin", "SGLT2 Inhibitor"),
        ("Ertugliflozin", "SGLT2 Inhibitor"),
        ("Insulin Glargine", "Long-acting Insulin Analogue"),
        ("Insulin Degludec", "Ultra-long-acting Insulin Analogue"),
        ("Insulin Detemir", "Long-acting Insulin Analogue"),
        ("Insulin Aspart", "Rapid-acting Insulin Analogue"),
        ("Insulin Lispro", "Rapid-acting Insulin Analogue"),
        ("Insulin Glulisine", "Rapid-acting Insulin Analogue"),
        ("Regular Insulin", "Short-acting Insulin"),
        ("NPH Insulin", "Intermediate-acting Insulin"),
        ("Levothyroxine", "Synthetic T4 Thyroid Hormone"),
        ("Liothyronine", "Synthetic T3 Thyroid Hormone"),
        ("Methimazole", "Thioamide Antithyroid"),
        ("Propylthiouracil", "Thioamide Antithyroid"),
        ("Potassium Iodide", "Antithyroid"),
        ("Radioactive Iodine I-131", "Antithyroid"),
        ("Prednisone", "Glucocorticoid"),
        ("Prednisolone", "Glucocorticoid"),
        ("Methylprednisolone", "Glucocorticoid"),
        ("Dexamethasone", "Glucocorticoid"),
        ("Hydrocortisone", "Glucocorticoid"),
        ("Betamethasone", "Glucocorticoid"),
        ("Triamcinolone", "Glucocorticoid"),
        ("Fludrocortisone", "Mineralocorticoid"),
        ("Growth Hormone Somatropin", "Recombinant Human Growth Hormone"),
        ("Octreotide", "Somatostatin Analogue"),
        ("Lanreotide", "Somatostatin Analogue"),
        ("Desmopressin", "ADH Analogue"),
        ("Tolvaptan", "Vasopressin V2 Receptor Antagonist"),
        ("Cinacalcet", "Calcimimetic"),
        ("Calcitonin", "Antiresorptive"),
        ("Alendronate", "Bisphosphonate"),
        ("Risedronate", "Bisphosphonate"),
        ("Ibandronate", "Bisphosphonate"),
        ("Zoledronic Acid", "Bisphosphonate"),
        ("Teriparatide", "Parathyroid Hormone Analogue"),
        ("Abaloparatide", "Parathyroid Hormone-related Protein Analogue"),
        ("Romosozumab", "Sclerostin Inhibitor"),
        ("Denosumab", "RANK Ligand Inhibitor"),
        ("Testosterone", "Androgen"),
        ("Finasteride", "5-Alpha Reductase Inhibitor"),
        ("Dutasteride", "5-Alpha Reductase Inhibitor"),
        ("Estradiol", "Estrogen"),
        ("Progesterone", "Progestogen"),
        ("Medroxyprogesterone", "Progestogen"),
        ("Combined Oral Contraceptive", "Estrogen-Progestin Combination"),
        ("Levonorgestrel", "Progestogen-only Contraceptive"),
        ("Clomiphene", "Selective Estrogen Receptor Modulator"),
        ("Tamoxifen", "Selective Estrogen Receptor Modulator"),
        ("Raloxifene", "Selective Estrogen Receptor Modulator"),
        ("Aromatase Inhibitor Anastrozole", "Aromatase Inhibitor"),
        ("Letrozole", "Aromatase Inhibitor"),
    ],

    "gi_hepatology": [
        ("Omeprazole", "Proton Pump Inhibitor"),
        ("Pantoprazole", "Proton Pump Inhibitor"),
        ("Lansoprazole", "Proton Pump Inhibitor"),
        ("Rabeprazole", "Proton Pump Inhibitor"),
        ("Esomeprazole", "Proton Pump Inhibitor"),
        ("Dexlansoprazole", "Proton Pump Inhibitor"),
        ("Vonoprazan", "Potassium-competitive Acid Blocker"),
        ("Famotidine", "H2 Receptor Antagonist"),
        ("Cimetidine", "H2 Receptor Antagonist"),
        ("Ranitidine", "H2 Receptor Antagonist"),
        ("Sucralfate", "Cytoprotective"),
        ("Misoprostol", "Prostaglandin E1 Analogue"),
        ("Bismuth Subsalicylate", "Antidiarrheal / H. pylori treatment"),
        ("Metoclopramide", "Dopamine Antagonist / Prokinetic"),
        ("Ondansetron", "5-HT3 Antagonist"),
        ("Granisetron", "5-HT3 Antagonist"),
        ("Palonosetron", "5-HT3 Antagonist"),
        ("Dolasetron", "5-HT3 Antagonist"),
        ("Aprepitant", "NK1 Receptor Antagonist"),
        ("Rolapitant", "NK1 Receptor Antagonist"),
        ("Dexamethasone", "Glucocorticoid / Antiemetic"),
        ("Prochlorperazine", "Dopamine Antagonist / Antiemetic"),
        ("Promethazine", "Antihistamine / Antiemetic"),
        ("Scopolamine", "Anticholinergic / Antiemetic"),
        ("Loperamide", "Opioid-like Antidiarrheal"),
        ("Diphenoxylate-Atropine", "Antidiarrheal"),
        ("Bismuth Subsalicylate", "Antidiarrheal"),
        ("Lactulose", "Osmotic Laxative"),
        ("Polyethylene Glycol", "Osmotic Laxative"),
        ("Magnesium Hydroxide", "Saline Laxative"),
        ("Sennosides", "Stimulant Laxative"),
        ("Bisacodyl", "Stimulant Laxative"),
        ("Linaclotide", "Guanylate Cyclase-C Agonist"),
        ("Lubiprostone", "Chloride Channel Activator"),
        ("Plecanatide", "Guanylate Cyclase-C Agonist"),
        ("Prucalopride", "Selective Serotonin 5-HT4 Agonist"),
        ("Alosetron", "5-HT3 Antagonist / IBS-D"),
        ("Eluxadoline", "Opioid Receptor Agonist-Antagonist / IBS-D"),
        ("Rifaximin", "Rifamycin / IBS-D"),
        ("Mesalamine", "5-Aminosalicylic Acid"),
        ("Sulfasalazine", "5-ASA / Sulfapyridine Combination"),
        ("Balsalazide", "5-Aminosalicylic Acid Prodrug"),
        ("Olsalazine", "5-Aminosalicylic Acid Dimer"),
        ("Azathioprine", "Thiopurine Immunomodulator"),
        ("Mercaptopurine", "Thiopurine Immunomodulator"),
        ("Infliximab", "TNF-alpha Inhibitor Monoclonal Antibody"),
        ("Adalimumab", "TNF-alpha Inhibitor Monoclonal Antibody"),
        ("Certolizumab Pegol", "TNF-alpha Inhibitor PEGylated"),
        ("Golimumab", "TNF-alpha Inhibitor Monoclonal Antibody"),
        ("Vedolizumab", "Anti-alpha4-beta7 Integrin"),
        ("Ustekinumab", "IL-12/23 Inhibitor"),
        ("Risankizumab", "IL-23 Inhibitor"),
        ("Mirikizumab", "IL-23 Inhibitor"),
        ("Tofacitinib", "JAK Inhibitor"),
        ("Upadacitinib", "JAK1 Inhibitor"),
        ("Ozanimod", "Sphingosine-1-Phosphate Receptor Modulator"),
        ("Lactulose", "Osmotic Laxative / Hepatic Encephalopathy"),
        ("Rifaximin", "Non-absorbable Antibiotic / Hepatic Encephalopathy"),
        ("Ursodeoxycholic Acid", "Bile Acid"),
        ("Obeticholic Acid", "Farnesoid X Receptor Agonist"),
        ("Cholestyramine", "Bile Acid Sequestrant"),
        ("Terlipressin", "Vasopressin Analogue"),
        ("Octreotide", "Somatostatin Analogue"),
        ("Propranolol", "Beta Blocker / Portal Hypertension"),
        ("Carvedilol", "Alpha-Beta Blocker / Portal Hypertension"),
    ],

    "pulmonary": [
        ("Salbutamol", "Short-acting Beta-2 Agonist"),
        ("Levalbuterol", "Short-acting Beta-2 Agonist"),
        ("Salmeterol", "Long-acting Beta-2 Agonist"),
        ("Formoterol", "Long-acting Beta-2 Agonist"),
        ("Indacaterol", "Ultra-long-acting Beta-2 Agonist"),
        ("Olodaterol", "Ultra-long-acting Beta-2 Agonist"),
        ("Vilanterol", "Ultra-long-acting Beta-2 Agonist"),
        ("Ipratropium", "Short-acting Muscarinic Antagonist"),
        ("Tiotropium", "Long-acting Muscarinic Antagonist"),
        ("Aclidinium", "Long-acting Muscarinic Antagonist"),
        ("Glycopyrrolate", "Long-acting Muscarinic Antagonist"),
        ("Umeclidinium", "Long-acting Muscarinic Antagonist"),
        ("Revefenacin", "Long-acting Muscarinic Antagonist"),
        ("Beclomethasone", "Inhaled Corticosteroid"),
        ("Fluticasone Propionate", "Inhaled Corticosteroid"),
        ("Fluticasone Furoate", "Inhaled Corticosteroid"),
        ("Budesonide", "Inhaled Corticosteroid"),
        ("Mometasone", "Inhaled Corticosteroid"),
        ("Ciclesonide", "Inhaled Corticosteroid"),
        ("Montelukast", "Leukotriene Receptor Antagonist"),
        ("Zafirlukast", "Leukotriene Receptor Antagonist"),
        ("Zileuton", "5-Lipoxygenase Inhibitor"),
        ("Theophylline", "Methylxanthine / Phosphodiesterase Inhibitor"),
        ("Roflumilast", "PDE4 Inhibitor"),
        ("Omalizumab", "Anti-IgE Monoclonal Antibody"),
        ("Mepolizumab", "Anti-IL-5 Monoclonal Antibody"),
        ("Reslizumab", "Anti-IL-5 Monoclonal Antibody"),
        ("Benralizumab", "Anti-IL-5 Receptor Monoclonal Antibody"),
        ("Dupilumab", "Anti-IL-4/13 Monoclonal Antibody"),
        ("Tezepelumab", "Anti-TSLP Monoclonal Antibody"),
        ("Azithromycin", "Macrolide / Anti-inflammatory in COPD"),
        ("N-Acetylcysteine", "Mucolytic"),
        ("Dornase Alfa", "DNase / Mucolytic"),
        ("Ivacaftor", "CFTR Potentiator"),
        ("Lumacaftor-Ivacaftor", "CFTR Corrector-Potentiator"),
        ("Tezacaftor-Ivacaftor", "CFTR Corrector-Potentiator"),
        ("Elexacaftor-Tezacaftor-Ivacaftor", "Triple CFTR Modulator"),
        ("Sildenafil", "PDE5 Inhibitor / Pulmonary Hypertension"),
        ("Ambrisentan", "Endothelin Receptor Antagonist"),
        ("Macitentan", "Endothelin Receptor Antagonist"),
        ("Riociguat", "Soluble Guanylate Cyclase Stimulator"),
        ("Treprostinil", "Prostacyclin Analogue"),
        ("Iloprost", "Prostacyclin Analogue"),
        ("Epoprostenol", "Prostacyclin"),
        ("Selexipag", "IP Prostacyclin Receptor Agonist"),
        ("Nintedanib", "Tyrosine Kinase Inhibitor / IPF"),
        ("Pirfenidone", "Antifibrotic"),
    ],

    "pain_rheumatology": [
        ("Acetaminophen", "Analgesic / Antipyretic"),
        ("Ibuprofen", "Non-selective NSAID"),
        ("Naproxen", "Non-selective NSAID"),
        ("Diclofenac", "Non-selective NSAID"),
        ("Ketorolac", "Non-selective NSAID"),
        ("Indomethacin", "Non-selective NSAID"),
        ("Meloxicam", "Preferential COX-2 Inhibitor"),
        ("Celecoxib", "Selective COX-2 Inhibitor"),
        ("Morphine", "Full Opioid Agonist"),
        ("Oxycodone", "Full Opioid Agonist"),
        ("Hydrocodone", "Full Opioid Agonist"),
        ("Hydromorphone", "Full Opioid Agonist"),
        ("Fentanyl", "Full Opioid Agonist"),
        ("Codeine", "Opioid Prodrug"),
        ("Tramadol", "Weak Opioid Agonist / SNRI"),
        ("Tapentadol", "Opioid Agonist / NRI"),
        ("Buprenorphine", "Partial Opioid Agonist"),
        ("Methadone", "Full Opioid Agonist / NMDA Antagonist"),
        ("Pregabalin", "Anticonvulsant / Neuropathic Pain"),
        ("Gabapentin", "Anticonvulsant / Neuropathic Pain"),
        ("Duloxetine", "SNRI / Neuropathic Pain"),
        ("Amitriptyline", "TCA / Neuropathic Pain"),
        ("Lidocaine Patch", "Topical Anesthetic"),
        ("Capsaicin", "TRPV1 Agonist / Topical Analgesic"),
        ("Hydroxychloroquine", "Antimalarial / DMARD"),
        ("Methotrexate", "Antifolate / DMARD"),
        ("Sulfasalazine", "DMARD"),
        ("Leflunomide", "Pyrimidine Synthesis Inhibitor / DMARD"),
        ("Abatacept", "T-cell Costimulation Modulator"),
        ("Tocilizumab", "IL-6 Receptor Inhibitor"),
        ("Sarilumab", "IL-6 Receptor Inhibitor"),
        ("Rituximab", "Anti-CD20 Monoclonal Antibody"),
        ("Adalimumab", "TNF-alpha Inhibitor"),
        ("Etanercept", "TNF-alpha Receptor Fusion Protein"),
        ("Infliximab", "TNF-alpha Inhibitor"),
        ("Certolizumab Pegol", "TNF-alpha Inhibitor"),
        ("Golimumab", "TNF-alpha Inhibitor"),
        ("Tofacitinib", "JAK Inhibitor"),
        ("Baricitinib", "JAK Inhibitor"),
        ("Upadacitinib", "JAK1 Inhibitor"),
        ("Filgotinib", "JAK1 Inhibitor"),
        ("Secukinumab", "IL-17A Inhibitor"),
        ("Ixekizumab", "IL-17A Inhibitor"),
        ("Bimekizumab", "IL-17A/F Inhibitor"),
        ("Ustekinumab", "IL-12/23 Inhibitor"),
        ("Guselkumab", "IL-23 Inhibitor"),
        ("Risankizumab", "IL-23 Inhibitor"),
        ("Allopurinol", "Xanthine Oxidase Inhibitor"),
        ("Febuxostat", "Xanthine Oxidase Inhibitor"),
        ("Probenecid", "Uricosuric Agent"),
        ("Colchicine", "Tubulin Polymerization Inhibitor"),
        ("Pegloticase", "Uricase"),
        ("Rasburicase", "Recombinant Urate Oxidase"),
        ("Belimumab", "BLyS Inhibitor / Lupus"),
        ("Anifrolumab", "Type I Interferon Receptor Antagonist / Lupus"),
    ],

    "oncology": [
        ("Cyclophosphamide", "Alkylating Agent"),
        ("Ifosfamide", "Alkylating Agent"),
        ("Temozolomide", "Alkylating Agent"),
        ("Carboplatin", "Platinum-based Alkylating Agent"),
        ("Cisplatin", "Platinum-based Alkylating Agent"),
        ("Oxaliplatin", "Platinum-based Alkylating Agent"),
        ("Methotrexate", "Antifolate"),
        ("Fluorouracil", "Pyrimidine Antimetabolite"),
        ("Capecitabine", "Oral Pyrimidine Antimetabolite Prodrug"),
        ("Gemcitabine", "Pyrimidine Antimetabolite"),
        ("Pemetrexed", "Multi-targeted Antifolate"),
        ("Vincristine", "Vinca Alkaloid"),
        ("Vinblastine", "Vinca Alkaloid"),
        ("Vinorelbine", "Vinca Alkaloid"),
        ("Paclitaxel", "Taxane"),
        ("Docetaxel", "Taxane"),
        ("Nab-Paclitaxel", "Albumin-bound Taxane"),
        ("Cabazitaxel", "Taxane"),
        ("Doxorubicin", "Anthracycline"),
        ("Epirubicin", "Anthracycline"),
        ("Daunorubicin", "Anthracycline"),
        ("Idarubicin", "Anthracycline"),
        ("Topotecan", "Topoisomerase I Inhibitor"),
        ("Irinotecan", "Topoisomerase I Inhibitor"),
        ("Etoposide", "Topoisomerase II Inhibitor"),
        ("Bleomycin", "Glycopeptide Antibiotic / Antitumor"),
        ("Rituximab", "Anti-CD20 Monoclonal Antibody"),
        ("Trastuzumab", "Anti-HER2 Monoclonal Antibody"),
        ("Pertuzumab", "Anti-HER2 Monoclonal Antibody"),
        ("Bevacizumab", "Anti-VEGF Monoclonal Antibody"),
        ("Cetuximab", "Anti-EGFR Monoclonal Antibody"),
        ("Pembrolizumab", "PD-1 Checkpoint Inhibitor"),
        ("Nivolumab", "PD-1 Checkpoint Inhibitor"),
        ("Ipilimumab", "CTLA-4 Checkpoint Inhibitor"),
        ("Atezolizumab", "PD-L1 Checkpoint Inhibitor"),
        ("Durvalumab", "PD-L1 Checkpoint Inhibitor"),
        ("Avelumab", "PD-L1 Checkpoint Inhibitor"),
        ("Imatinib", "BCR-ABL Tyrosine Kinase Inhibitor"),
        ("Dasatinib", "BCR-ABL Tyrosine Kinase Inhibitor"),
        ("Nilotinib", "BCR-ABL Tyrosine Kinase Inhibitor"),
        ("Erlotinib", "EGFR Tyrosine Kinase Inhibitor"),
        ("Gefitinib", "EGFR Tyrosine Kinase Inhibitor"),
        ("Osimertinib", "Third-gen EGFR TKI"),
        ("Vemurafenib", "BRAF V600E Inhibitor"),
        ("Dabrafenib", "BRAF V600E Inhibitor"),
        ("Trametinib", "MEK Inhibitor"),
        ("Crizotinib", "ALK/ROS1 Inhibitor"),
        ("Alectinib", "ALK Inhibitor"),
        ("Lorlatinib", "ALK Inhibitor"),
        ("Palbociclib", "CDK4/6 Inhibitor"),
        ("Ribociclib", "CDK4/6 Inhibitor"),
        ("Abemaciclib", "CDK4/6 Inhibitor"),
        ("Olaparib", "PARP Inhibitor"),
        ("Rucaparib", "PARP Inhibitor"),
        ("Niraparib", "PARP Inhibitor"),
        ("Talazoparib", "PARP Inhibitor"),
        ("Venetoclax", "BCL-2 Inhibitor"),
        ("Ibrutinib", "BTK Inhibitor"),
        ("Acalabrutinib", "BTK Inhibitor"),
        ("Zanubrutinib", "BTK Inhibitor"),
        ("Idelalisib", "PI3K-delta Inhibitor"),
        ("Copanlisib", "PI3K Inhibitor"),
        ("Lenalidomide", "Immunomodulatory Agent"),
        ("Thalidomide", "Immunomodulatory Agent"),
        ("Pomalidomide", "Immunomodulatory Agent"),
        ("Bortezomib", "Proteasome Inhibitor"),
        ("Carfilzomib", "Proteasome Inhibitor"),
        ("Ixazomib", "Proteasome Inhibitor"),
        ("Daratumumab", "Anti-CD38 Monoclonal Antibody"),
        ("Elotuzumab", "Anti-SLAMF7 Monoclonal Antibody"),
        ("Azacitidine", "DNA Methyltransferase Inhibitor"),
        ("Decitabine", "DNA Methyltransferase Inhibitor"),
        ("Midostaurin", "FLT3/KIT Inhibitor"),
        ("Enasidenib", "IDH2 Inhibitor"),
        ("Ivosidenib", "IDH1 Inhibitor"),
        ("Gilteritinib", "FLT3 Inhibitor"),
        ("Glasdegib", "Hedgehog Pathway Inhibitor"),
        ("Asparaginase", "Enzyme"),
    ],

    "nephrology_urology": [
        ("Furosemide", "Loop Diuretic"),
        ("Tolvaptan", "V2 Receptor Antagonist"),
        ("Desmopressin", "ADH Analogue"),
        ("Sodium Bicarbonate", "Alkalinizing Agent"),
        ("Kayexalate", "Cation Exchange Resin"),
        ("Patiromer", "Potassium Binder"),
        ("Sodium Zirconium Cyclosilicate", "Potassium Binder"),
        ("Cinacalcet", "Calcimimetic"),
        ("Sevelamer", "Phosphate Binder"),
        ("Calcium Carbonate", "Phosphate Binder / Calcium Supplement"),
        ("Lanthanum Carbonate", "Phosphate Binder"),
        ("Erythropoietin Alfa", "Erythropoiesis-stimulating Agent"),
        ("Darbepoetin Alfa", "Erythropoiesis-stimulating Agent"),
        ("Iron Sucrose", "IV Iron Supplement"),
        ("Ferric Carboxymaltose", "IV Iron Supplement"),
        ("Ferumoxytol", "IV Iron Supplement"),
        ("Tamsulosin", "Alpha-1A Adrenergic Antagonist"),
        ("Alfuzosin", "Alpha-1 Adrenergic Antagonist"),
        ("Doxazosin", "Alpha-1 Adrenergic Antagonist"),
        ("Terazosin", "Alpha-1 Adrenergic Antagonist"),
        ("Silodosin", "Alpha-1A Adrenergic Antagonist"),
        ("Finasteride", "5-Alpha Reductase Inhibitor"),
        ("Dutasteride", "5-Alpha Reductase Inhibitor"),
        ("Oxybutynin", "Anticholinergic / Overactive Bladder"),
        ("Tolterodine", "Anticholinergic / Overactive Bladder"),
        ("Solifenacin", "Anticholinergic / Overactive Bladder"),
        ("Darifenacin", "Anticholinergic / Overactive Bladder"),
        ("Mirabegron", "Beta-3 Adrenergic Agonist / Overactive Bladder"),
        ("Vibegron", "Beta-3 Adrenergic Agonist / Overactive Bladder"),
        ("Fesoterodine", "Anticholinergic / Overactive Bladder"),
        ("Sildenafil", "PDE5 Inhibitor / Erectile Dysfunction"),
        ("Tadalafil", "PDE5 Inhibitor / Erectile Dysfunction"),
        ("Vardenafil", "PDE5 Inhibitor / Erectile Dysfunction"),
        ("Avanafil", "PDE5 Inhibitor / Erectile Dysfunction"),
        ("Nitrofurantoin", "Nitrofuran Antibiotic / UTI"),
        ("Fosfomycin", "Phosphonic Acid / UTI"),
        ("Trimethoprim", "DHFR Inhibitor / UTI"),
    ],

    "hematology": [
        ("Warfarin", "Vitamin K Antagonist"),
        ("Heparin Unfractionated", "Indirect Thrombin Inhibitor"),
        ("Enoxaparin", "Low Molecular Weight Heparin"),
        ("Fondaparinux", "Factor Xa Inhibitor"),
        ("Rivaroxaban", "Direct Factor Xa Inhibitor"),
        ("Apixaban", "Direct Factor Xa Inhibitor"),
        ("Dabigatran", "Direct Thrombin Inhibitor"),
        ("Edoxaban", "Direct Factor Xa Inhibitor"),
        ("Argatroban", "Direct Thrombin Inhibitor"),
        ("Bivalirudin", "Direct Thrombin Inhibitor"),
        ("Alteplase", "Tissue Plasminogen Activator"),
        ("Tenecteplase", "Tissue Plasminogen Activator"),
        ("Factor VIII Concentrate", "Clotting Factor Replacement"),
        ("Factor IX Concentrate", "Clotting Factor Replacement"),
        ("Emicizumab", "Bispecific Antibody Factor VIII Mimetic"),
        ("Fitusiran", "Antithrombin siRNA"),
        ("Desmopressin", "ADH Analogue / Hemostasis"),
        ("Tranexamic Acid", "Antifibrinolytic"),
        ("Aminocaproic Acid", "Antifibrinolytic"),
        ("Protamine Sulfate", "Heparin Reversal"),
        ("Idarucizumab", "Dabigatran Reversal"),
        ("Andexanet Alfa", "Factor Xa Inhibitor Reversal"),
        ("Vitamin K", "Coagulation Factor Synthesis"),
        ("Hydroxyurea", "Ribonucleotide Reductase Inhibitor"),
        ("Voxelotor", "Hemoglobin S Polymerization Inhibitor"),
        ("Crizanlizumab", "Anti-P-selectin Monoclonal Antibody"),
        ("Luspatercept", "Erythroid Maturation Agent"),
        ("Roxadustat", "HIF-PH Inhibitor"),
        ("Filgrastim", "G-CSF"),
        ("Pegfilgrastim", "Long-acting G-CSF"),
        ("Sargramostim", "GM-CSF"),
        ("Eltrombopag", "Thrombopoietin Receptor Agonist"),
        ("Romiplostim", "Thrombopoietin Receptor Agonist"),
        ("Avatrombopag", "Thrombopoietin Receptor Agonist"),
        ("Lusutrombopag", "Thrombopoietin Receptor Agonist"),
        ("Iron Dextran", "IV Iron Supplement"),
        ("Ferric Gluconate", "IV Iron Supplement"),
        ("Deferasirox", "Oral Iron Chelator"),
        ("Deferoxamine", "Parenteral Iron Chelator"),
        ("Phytonadione", "Vitamin K1"),
    ],

    "dermatology": [
        ("Tretinoin", "Topical Retinoid"),
        ("Adapalene", "Topical Retinoid"),
        ("Tazarotene", "Topical Retinoid"),
        ("Isotretinoin", "Systemic Retinoid"),
        ("Acitretin", "Systemic Retinoid"),
        ("Benzoyl Peroxide", "Antimicrobial / Keratolytic"),
        ("Clindamycin Topical", "Topical Antibiotic"),
        ("Erythromycin Topical", "Topical Antibiotic"),
        ("Doxycycline", "Tetracycline / Acne"),
        ("Salicylic Acid", "Keratolytic"),
        ("Clobetasol", "Ultra-high Potency Topical Corticosteroid"),
        ("Betamethasone Dipropionate", "High Potency Topical Corticosteroid"),
        ("Triamcinolone Acetonide", "Medium Potency Topical Corticosteroid"),
        ("Hydrocortisone Topical", "Low Potency Topical Corticosteroid"),
        ("Tacrolimus Topical", "Calcineurin Inhibitor"),
        ("Pimecrolimus", "Calcineurin Inhibitor"),
        ("Crisaborole", "PDE4 Inhibitor / Topical"),
        ("Ruxolitinib Cream", "JAK1/2 Inhibitor / Topical"),
        ("Dupilumab", "Anti-IL-4/13 Monoclonal Antibody"),
        ("Tralokinumab", "Anti-IL-13 Monoclonal Antibody"),
        ("Lebrikizumab", "Anti-IL-13 Monoclonal Antibody"),
        ("Secukinumab", "Anti-IL-17A / Psoriasis"),
        ("Ixekizumab", "Anti-IL-17A / Psoriasis"),
        ("Risankizumab", "Anti-IL-23 / Psoriasis"),
        ("Bimekizumab", "Anti-IL-17A/F / Psoriasis"),
        ("Calcipotriene", "Vitamin D3 Analogue"),
        ("Coal Tar", "Antipsoriatic"),
        ("Anthralin", "Antipsoriatic"),
        ("Terbinafine", "Allylamine Antifungal"),
        ("Clotrimazole", "Azole Antifungal"),
        ("Econazole", "Azole Antifungal"),
        ("Mupirocin", "Topical Antibiotic"),
        ("Azelaic Acid", "Topical Keratolytic / Antibacterial"),
        ("Ivermectin Topical", "Topical Antiparasitic / Rosacea"),
        ("Metronidazole Topical", "Topical Antibiotic / Rosacea"),
        ("Oxymetazoline", "Alpha Agonist / Rosacea"),
        ("Omalizumab", "Anti-IgE / Chronic Urticaria"),
        ("Deucravacitinib", "TYK2 Inhibitor / Psoriasis"),
        ("Spesolimab", "Anti-IL-36R / GPP"),
    ],

    "emergency_critical": [
        ("Epinephrine", "Catecholamine / Vasopressor"),
        ("Norepinephrine", "Catecholamine / Vasopressor"),
        ("Dopamine", "Catecholamine"),
        ("Dobutamine", "Beta-1 Agonist / Inotrope"),
        ("Vasopressin", "ADH / Vasopressor"),
        ("Phenylephrine", "Alpha-1 Agonist / Vasopressor"),
        ("Milrinone", "PDE3 Inhibitor / Inotrope"),
        ("Atropine", "Muscarinic Antagonist / Bradycardia"),
        ("Adenosine", "Antiarrhythmic / SVT"),
        ("Sodium Bicarbonate", "Alkalinizing Agent / Resuscitation"),
        ("Calcium Chloride", "Calcium / Resuscitation"),
        ("Calcium Gluconate", "Calcium / Hypocalcemia"),
        ("Magnesium Sulfate", "Electrolyte / Tocolytic / Anticonvulsant"),
        ("Naloxone", "Opioid Antagonist"),
        ("Flumazenil", "Benzodiazepine Antagonist"),
        ("Activated Charcoal", "GI Decontaminant"),
        ("N-Acetylcysteine", "Antidote / Acetaminophen Overdose"),
        ("Dextrose 50%", "Glucose Solution / Hypoglycemia"),
        ("Glucagon", "Glycogenolytic Hormone"),
        ("Hydroxocobalamin", "Cyanide Antidote"),
        ("Methylene Blue", "Methemoglobinemia Treatment"),
        ("Physostigmine", "Cholinesterase Inhibitor / Anticholinergic Reversal"),
        ("Pralidoxime", "Organophosphate Antidote"),
        ("Fomepizole", "Alcohol Dehydrogenase Inhibitor / Toxic Alcohol Antidote"),
        ("Diphenhydramine", "Antihistamine / Anaphylaxis"),
        ("Methylprednisolone", "Corticosteroid / Anaphylaxis"),
        ("Rocuronium", "Non-depolarizing Neuromuscular Blocker"),
        ("Vecuronium", "Non-depolarizing Neuromuscular Blocker"),
        ("Succinylcholine", "Depolarizing Neuromuscular Blocker"),
        ("Sugammadex", "Neuromuscular Blockade Reversal"),
        ("Neostigmine", "Cholinesterase Inhibitor / NMB Reversal"),
        ("Ketamine", "Dissociative Anesthetic"),
        ("Propofol", "Intravenous Anesthetic"),
        ("Etomidate", "Intravenous Anesthetic"),
        ("Fentanyl", "Opioid Analgesic"),
        ("Hydromorphone", "Opioid Analgesic"),
        ("Dexmedetomidine", "Alpha-2 Agonist / Sedation"),
        ("Lorazepam", "Benzodiazepine / Sedation"),
        ("Midazolam", "Benzodiazepine / Sedation"),
        ("Phenytoin", "Anticonvulsant / Status Epilepticus"),
        ("Levetiracetam", "Anticonvulsant / Status Epilepticus"),
        ("Valproate IV", "Anticonvulsant / Status Epilepticus"),
        ("Labetalol IV", "Alpha-Beta Blocker / Hypertensive Emergency"),
        ("Nicardipine IV", "CCB / Hypertensive Emergency"),
        ("Hydralazine IV", "Vasodilator / Hypertensive Emergency"),
        ("Nitroprusside IV", "Direct Vasodilator / Hypertensive Emergency"),
        ("Furosemide IV", "Loop Diuretic / Acute Pulmonary Edema"),
        ("Mannitol", "Osmotic Diuretic / Increased ICP"),
        ("Hypertonic Saline 3%", "Osmotic / Hyponatremia / ICP"),
        ("Alteplase IV", "tPA / Acute Ischemic Stroke"),
        ("Heparin IV", "Anticoagulant"),
        ("Vancomycin IV", "Glycopeptide / Sepsis"),
        ("Piperacillin-Tazobactam IV", "Antipseudomonal / Sepsis"),
        ("Meropenem IV", "Carbapenem / Sepsis"),
        ("Hydrocortisone IV", "Corticosteroid / Septic Shock"),
        ("Insulin Drip", "Insulin / DKA / HHS"),
        ("Nitrates IV", "Vasodilator / Acute Coronary Syndrome"),
        ("Amiodarone IV", "Antiarrhythmic / VT/VF"),
        ("Lidocaine IV", "Antiarrhythmic / VT"),
    ],
}


DRUG_PROMPT = """\
You are a clinical pharmacologist creating a medical education drug database.
Generate a comprehensive clinical profile for: {name} ({drug_class})

Use EXACTLY this output format (no extra text):

MECHANISM: [2-3 sentences describing mechanism of action with receptor targets]
INDICATIONS:
- [primary indication with FDA approval status if known]
- [secondary indication]
- [additional indications]
CONTRAINDICATIONS:
- [absolute contraindication]
- [relative contraindication]
DOSING:
Adult: [dose, route, frequency]
Renal: [GFR-based adjustment or "No adjustment needed"]
Hepatic: [Child-Pugh adjustment or "Use with caution"]
Pediatric: [weight-based dose or "Not approved <X years"]
ADVERSE_EFFECTS:
Common (>10%): [effect1, effect2, effect3]
Serious: [serious adverse effect, serious adverse effect]
Rare: [rare adverse effect]
MONITORING:
- [parameter to monitor with frequency/target]
- [lab value to watch]
INTERACTIONS:
- [major drug interaction and mechanism]
- [important interaction]
BLACK_BOX: [exact text of black box warning, or "None"]
HIGH_YIELD: [yes if commonly tested on boards, no otherwise]

Rules: Use specific numbers (doses, frequencies). Name drugs in interactions by their generic name."""


def _parse_drug_response(text: str) -> dict | None:
    """Parse structured drug profile response."""
    def _extract(label: str) -> str:
        m = re.search(rf"^{label}:\s*(.+?)(?=\n[A-Z_]+:|$)", text, re.MULTILINE | re.DOTALL)
        return m.group(1).strip() if m else ""

    def _extract_list(label: str) -> list[str]:
        block = _extract(label)
        if not block:
            return []
        items = []
        for line in block.splitlines():
            line = re.sub(r"^[-•*\d]+\.?\s*", "", line).strip()
            if line and not line.endswith(":"):
                items.append(line)
        return items

    mechanism = _extract("MECHANISM")
    if not mechanism or len(mechanism) < 20:
        return None

    indications     = _extract_list("INDICATIONS")
    contraindications = _extract_list("CONTRAINDICATIONS")
    monitoring      = _extract_list("MONITORING")
    interactions    = _extract_list("INTERACTIONS")
    black_box_raw   = _extract("BLACK_BOX")
    black_box       = None if black_box_raw.lower().strip() in ("none", "n/a", "") else black_box_raw
    high_yield      = "yes" in _extract("HIGH_YIELD").lower()

    # Parse adverse effects
    adverse_effects = {}
    ae_block = _extract("ADVERSE_EFFECTS")
    for line in ae_block.splitlines():
        m = re.match(r"^(\w[\w\s/]+?)\s*[:(>%\d]+.*?:\s*(.+)", line)
        if m:
            category = m.group(1).strip().title()
            effects = [e.strip() for e in m.group(2).split(",") if e.strip()]
            adverse_effects[category] = effects

    # Parse dosing
    dosing = {}
    dose_block = _extract("DOSING")
    for line in dose_block.splitlines():
        m = re.match(r"^(\w[\w\s]+?):\s*(.+)", line)
        if m:
            dosing[m.group(1).strip()] = m.group(2).strip()

    return {
        "mechanism": mechanism,
        "indications": indications,
        "contraindications": contraindications,
        "dosing": dosing,
        "adverse_effects": adverse_effects,
        "monitoring": monitoring,
        "interactions": interactions,
        "black_box_warning": black_box,
        "is_high_yield": high_yield,
    }


def load_groq_keys() -> list[str]:
    keys = []
    env_vars = ["GROQ_API_KEY"] + [f"GROQ_API_KEY_{i}" for i in range(2, 10)]
    env_file = os.path.join(os.path.dirname(__file__), "backend", ".env.prod")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                for var in env_vars:
                    if line.startswith(f"{var}="):
                        val = line.split("=", 1)[1].strip()
                        if val and val not in keys:
                            keys.append(val)
    return keys


def call_groq(prompt: str, keys: list[str], exhausted: set[int]) -> str | None:
    import datetime as _dt
    while len(exhausted) >= len(keys):
        now = _dt.datetime.utcnow()
        tomorrow = (now + _dt.timedelta(days=1)).replace(hour=0, minute=2, second=0, microsecond=0)
        wait = int((tomorrow - now).total_seconds())
        log.info("All Groq keys exhausted — sleeping %dh %dm", wait//3600, (wait%3600)//60)
        time.sleep(wait)
        exhausted.clear()

    for i, key in enumerate(keys):
        if i in exhausted:
            continue
        try:
            resp = httpx.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": GROQ_MODEL, "messages": [{"role":"user","content": prompt}],
                      "max_tokens": 1000, "temperature": 0.1},
                timeout=60,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            if resp.status_code == 429:
                retry = int(resp.headers.get("retry-after", "0") or "0")
                err = resp.json().get("error", {}).get("message", "")
                if retry > 3600 or "per day" in err.lower():
                    exhausted.add(i)
                    log.warning("Key %d/%d daily limit", i+1, len(keys))
                    continue
                time.sleep(min(retry+1, 30))
                # one retry
                resp2 = httpx.post(GROQ_URL,
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={"model": GROQ_MODEL, "messages":[{"role":"user","content":prompt}],
                          "max_tokens":1000, "temperature":0.1}, timeout=60)
                if resp2.status_code == 200:
                    return resp2.json()["choices"][0]["message"]["content"]
        except Exception as e:
            log.warning("Key %d error: %s", i+1, e)
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit",   type=int, default=0)
    parser.add_argument("--class",   dest="drug_class", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--delay",   type=float, default=1.5)
    args = parser.parse_args()

    conn = psycopg2.connect(DB_URL)

    # Load existing drug names for dedup
    with conn.cursor() as cur:
        cur.execute("SELECT LOWER(name), LOWER(COALESCE(generic_name,'')) FROM drugs")
        existing_names = {row[0] for row in cur.fetchall()} | {row[1] for row in cur.fetchall() if row[1]}

    # Build pending list
    pending: list[tuple[str, str, str]] = []  # (name, generic, drug_class)
    total_in_list = 0
    for drug_class_key, drugs in DRUG_LIST.items():
        if args.drug_class and drug_class_key != args.drug_class:
            continue
        for generic, drug_class in drugs:
            total_in_list += 1
            if generic.lower() in existing_names:
                continue
            # Also check partial matches
            first_word = generic.lower().split()[0]
            if any(first_word in name for name in existing_names):
                continue
            pending.append((generic, generic, drug_class))

    log.info("Drug list total: %d | Already in DB: %d | To generate: %d",
             total_in_list, total_in_list - len(pending), len(pending))

    if args.dry_run:
        for name, _, drug_class in pending[:50]:
            print(f"  {name} ({drug_class})")
        if len(pending) > 50:
            print(f"  ... and {len(pending)-50} more")
        print(f"\nTotal pending: {len(pending)}")
        conn.close()
        return

    if args.limit:
        pending = pending[:args.limit]

    keys = load_groq_keys()
    if not keys:
        print("❌ No GROQ_API_KEY found")
        sys.exit(1)
    log.info("Using %d Groq keys", len(keys))

    exhausted: set[int] = set()
    done = skipped = errors = 0

    for name, generic_name, drug_class in pending:
        log.info("[%d/%d] %s (%s)", done+1, len(pending), name, drug_class)

        prompt = DRUG_PROMPT.format(name=name, drug_class=drug_class)
        raw = call_groq(prompt, keys, exhausted)
        if not raw:
            errors += 1
            continue

        parsed = _parse_drug_response(raw)
        if not parsed:
            log.warning("  Parse failed: %s", raw[:200])
            errors += 1
            continue

        drug_id = str(uuid.uuid4())
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO drugs (
                        id, name, generic_name, drug_class, mechanism,
                        indications, contraindications, dosing, adverse_effects,
                        monitoring, interactions, black_box_warning,
                        is_high_yield, is_nti, is_veterinary, created_at
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s::jsonb, %s::jsonb,
                        %s, %s, %s,
                        %s, false, false, NOW()
                    )
                    ON CONFLICT DO NOTHING
                """, (
                    drug_id, name, generic_name, drug_class,
                    parsed["mechanism"],
                    parsed["indications"],
                    parsed["contraindications"],
                    json.dumps(parsed["dosing"]),
                    json.dumps(parsed["adverse_effects"]),
                    parsed["monitoring"],
                    parsed["interactions"],
                    parsed["black_box_warning"],
                    parsed["is_high_yield"],
                ))
            conn.commit()
            log.info("  ✓ Added: %s", name)
            done += 1
        except Exception as e:
            conn.rollback()
            log.error("  DB error: %s", e)
            errors += 1

        time.sleep(args.delay)

    conn.close()
    log.info("="*50)
    log.info("Done. Added: %d | Skipped: %d | Errors: %d", done, skipped, errors)
    log.info("Total drugs now: run 'SELECT COUNT(*) FROM drugs;'")

    # Auto-run image fetch for new drugs
    log.info("Fetching Wikipedia images for new drugs…")
    os.system("python3 fetch_drug_images.py >> /tmp/drug_images.log 2>&1")
    log.info("Starting translations…")
    os.system("nohup python3 translate_drugs.py >> /tmp/drug_translate.log 2>&1 &")


if __name__ == "__main__":
    main()
