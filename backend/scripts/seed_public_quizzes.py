"""Seed 5 starter public quizzes for Phase 4.

Idempotent — safe to run multiple times.
"""
import asyncio
import uuid
from sqlalchemy import select, text
from app.core.database import engine, AsyncSessionLocal
from app.models.models import PublicQuiz

QUIZZES = [
    {
        "slug": "first-aid-essentials",
        "title": "First Aid Essentials",
        "description": "Do you know what to do in a medical emergency? Test your first-aid knowledge — no medical degree required.",
        "category": "first-aid",
        "questions": [
            {
                "question": "Someone collapses and is unresponsive. What is the first thing you should do?",
                "options": {
                    "A": "Give them water",
                    "B": "Check for breathing and call emergency services",
                    "C": "Slap their face to wake them up",
                    "D": "Wait a few minutes to see if they recover"
                },
                "correct": "B",
                "explanation": "Always check for breathing and call 112/911 immediately. Early activation of emergency services is critical in any life-threatening situation."
            },
            {
                "question": "What does CPR stand for?",
                "options": {
                    "A": "Cardiac Pressure Response",
                    "B": "Cardiopulmonary Resuscitation",
                    "C": "Critical Patient Recovery",
                    "D": "Chest Pressure Rhythm"
                },
                "correct": "B",
                "explanation": "CPR stands for Cardiopulmonary Resuscitation — a lifesaving technique combining chest compressions and rescue breaths to maintain circulation."
            },
            {
                "question": "For adult CPR, how many chest compressions per minute should you aim for?",
                "options": {
                    "A": "40–60",
                    "B": "60–80",
                    "C": "100–120",
                    "D": "130–150"
                },
                "correct": "C",
                "explanation": "Current guidelines recommend 100–120 compressions per minute — roughly to the beat of 'Stayin' Alive' by the Bee Gees."
            },
            {
                "question": "Someone has a severe nosebleed. What should you do?",
                "options": {
                    "A": "Tilt their head backward",
                    "B": "Pack their nose with cotton and tilt back",
                    "C": "Lean forward and pinch the soft part of the nose",
                    "D": "Lie them flat on their back"
                },
                "correct": "C",
                "explanation": "Lean forward (not backward — swallowing blood can cause nausea) and pinch the soft part of the nose firmly for 10–15 minutes."
            },
            {
                "question": "A child has swallowed a household chemical. What should you do first?",
                "options": {
                    "A": "Make them vomit immediately",
                    "B": "Give them milk to neutralize the poison",
                    "C": "Call Poison Control / emergency services",
                    "D": "Give them lots of water"
                },
                "correct": "C",
                "explanation": "Always call Poison Control or emergency services first. Do NOT induce vomiting — some chemicals cause more damage coming back up."
            },
            {
                "question": "What is the correct way to treat a minor burn?",
                "options": {
                    "A": "Apply butter or oil",
                    "B": "Pop any blisters that form",
                    "C": "Cool with running water for 10–20 minutes",
                    "D": "Cover immediately with a thick bandage"
                },
                "correct": "C",
                "explanation": "Cool the burn with cool (not ice cold) running water for 10–20 minutes. Never use butter, oil, or ice — they trap heat and worsen damage."
            },
            {
                "question": "Someone is having a seizure. You should:",
                "options": {
                    "A": "Hold them down to stop the shaking",
                    "B": "Put something in their mouth so they don't bite their tongue",
                    "C": "Clear the area, protect their head, time the seizure",
                    "D": "Give them water to drink"
                },
                "correct": "C",
                "explanation": "Never restrain someone during a seizure or put anything in their mouth. Clear the area, cushion their head, and time the seizure. Call 112 if it lasts >5 minutes."
            },
            {
                "question": "What is the 'Recovery Position' used for?",
                "options": {
                    "A": "Performing CPR more easily",
                    "B": "Keeping an unconscious breathing person safe while awaiting help",
                    "C": "Treating a broken leg",
                    "D": "Helping someone who is choking"
                },
                "correct": "B",
                "explanation": "The recovery position keeps an unconscious but breathing person on their side, preventing choking if they vomit while help is on the way."
            },
        ],
    },
    {
        "slug": "drug-myths-debunked",
        "title": "Drug Myths Debunked",
        "description": "Separate fact from fiction about common medications. What do you really know about the pills in your medicine cabinet?",
        "category": "pharmacology",
        "questions": [
            {
                "question": "TRUE or FALSE: Antibiotics work against viral infections like the common cold.",
                "options": {
                    "A": "True — antibiotics kill all infections",
                    "B": "False — antibiotics only work against bacteria",
                    "C": "True, but only strong antibiotics",
                    "D": "It depends on the type of cold"
                },
                "correct": "B",
                "explanation": "Antibiotics only work against bacterial infections. The common cold is caused by a virus. Misusing antibiotics contributes to antibiotic resistance — a global health crisis."
            },
            {
                "question": "If you feel better before finishing your antibiotic course, you should:",
                "options": {
                    "A": "Stop taking them — you're cured",
                    "B": "Finish the full course as prescribed",
                    "C": "Take double dose to finish faster",
                    "D": "Save the rest for next time you're sick"
                },
                "correct": "B",
                "explanation": "Always finish the full antibiotic course. Stopping early can allow surviving bacteria (often the most resistant ones) to multiply and cause a harder-to-treat infection."
            },
            {
                "question": "Is it safe to drink alcohol while taking paracetamol (acetaminophen)?",
                "options": {
                    "A": "Yes, it's completely safe",
                    "B": "Only if you drink in moderation",
                    "C": "No — the combination stresses the liver, especially with heavy drinking",
                    "D": "Only dangerous if taken together at the same time"
                },
                "correct": "C",
                "explanation": "Both alcohol and paracetamol are processed by the liver. Combining them — especially with regular or heavy drinking — significantly increases the risk of liver damage."
            },
            {
                "question": "Natural/herbal supplements:",
                "options": {
                    "A": "Are always safe because they're natural",
                    "B": "Cannot interact with prescription medications",
                    "C": "Can interact with medications and have real side effects",
                    "D": "Are regulated as strictly as prescription drugs"
                },
                "correct": "C",
                "explanation": "Natural does not mean safe. St. John's Wort, for example, reduces the effectiveness of contraceptives, blood thinners, and many other drugs. Always tell your doctor about supplements."
            },
            {
                "question": "Aspirin should generally be avoided in children under 16 because it can cause:",
                "options": {
                    "A": "Allergic reactions",
                    "B": "Reye's syndrome — a rare but serious brain and liver condition",
                    "C": "Tooth decay",
                    "D": "Kidney stones"
                },
                "correct": "B",
                "explanation": "Aspirin in children under 16 is linked to Reye's syndrome — a rare but potentially fatal condition affecting the brain and liver. Use paracetamol or ibuprofen for children instead."
            },
            {
                "question": "Expired medications are:",
                "options": {
                    "A": "Always dangerous to take",
                    "B": "Exactly as effective as fresh ones indefinitely",
                    "C": "Often less potent after the expiry date, and some (like tetracyclines) can become harmful",
                    "D": "Stronger than non-expired versions"
                },
                "correct": "C",
                "explanation": "Most medications lose potency after expiry. Some, notably old tetracycline antibiotics, can break down into toxic compounds. When in doubt, replace — never use expired medications for serious conditions."
            },
            {
                "question": "TRUE or FALSE: You can split any tablet in half to reduce the dose.",
                "options": {
                    "A": "True — splitting is always safe",
                    "B": "False — extended-release and enteric-coated tablets must NEVER be split",
                    "C": "True, as long as you use a clean knife",
                    "D": "Only capsules should not be split"
                },
                "correct": "B",
                "explanation": "Extended-release (XR, ER, XL) and enteric-coated tablets are designed to release medication gradually. Splitting destroys this mechanism and can cause dangerous overdose or loss of effect."
            },
            {
                "question": "Taking more than the recommended dose of a painkiller will:",
                "options": {
                    "A": "Relieve pain faster and more effectively",
                    "B": "Have no additional effect on pain but may cause serious harm",
                    "C": "Always just cause an upset stomach",
                    "D": "Be safe if you've taken it before"
                },
                "correct": "B",
                "explanation": "Exceeding the recommended dose rarely improves pain relief but significantly increases the risk of serious organ damage (liver with paracetamol, stomach/kidney/heart with NSAIDs). More is not better."
            },
        ],
    },
    {
        "slug": "warning-signs-see-a-doctor",
        "title": "Warning Signs: When to See a Doctor",
        "description": "Could you recognize a medical emergency? Test your ability to identify symptoms that need immediate attention.",
        "category": "symptoms",
        "questions": [
            {
                "question": "Which combination of symptoms could indicate a stroke? (Use FAST)",
                "options": {
                    "A": "Fever, Appetite loss, Sweating, Tiredness",
                    "B": "Face drooping, Arm weakness, Speech difficulty, Time to call emergency",
                    "C": "Fatigue, Aching joints, Slow digestion, Tingling",
                    "D": "Feeling cold, Anxiety, Stomach pain, Thirst"
                },
                "correct": "B",
                "explanation": "FAST: Face drooping, Arm weakness, Speech difficulty, Time to call 112/911. Strokes are medical emergencies where every minute counts — brain cells die rapidly without treatment."
            },
            {
                "question": "Chest pain that radiates to the left arm and jaw, with shortness of breath, is most likely:",
                "options": {
                    "A": "Heartburn",
                    "B": "Muscle strain",
                    "C": "A possible heart attack — call emergency services immediately",
                    "D": "Anxiety"
                },
                "correct": "C",
                "explanation": "These are classic heart attack warning signs. Call 112/911 immediately. Do not drive yourself to hospital. Chew aspirin if available and not allergic. Time lost = heart muscle lost."
            },
            {
                "question": "A sudden severe headache 'like the worst headache of your life' could indicate:",
                "options": {
                    "A": "Dehydration — drink more water",
                    "B": "Tension headache from stress",
                    "C": "A subarachnoid haemorrhage (brain bleed) — seek emergency care immediately",
                    "D": "Migraine — take your usual medication"
                },
                "correct": "C",
                "explanation": "A 'thunderclap' headache — sudden and severe, often described as the worst ever — is a red flag for subarachnoid haemorrhage. This is a life-threatening emergency requiring immediate hospital care."
            },
            {
                "question": "Dark, tarry (black and sticky) stools can indicate:",
                "options": {
                    "A": "Eating too many dark berries",
                    "B": "Bleeding somewhere in the upper digestive tract",
                    "C": "Iron deficiency",
                    "D": "Normal variation in bowel habits"
                },
                "correct": "B",
                "explanation": "Black tarry stools (melaena) are a sign of upper GI bleeding — blood from the stomach or small intestine turns black as it digests. This requires urgent medical evaluation."
            },
            {
                "question": "A rash that looks like a non-fading purple/red rash (doesn't blanch when pressed with a glass) could indicate:",
                "options": {
                    "A": "A mild allergic reaction",
                    "B": "Sunburn",
                    "C": "Meningococcal septicaemia — a life-threatening emergency",
                    "D": "Chickenpox"
                },
                "correct": "C",
                "explanation": "A non-blanching petechial/purpuric rash can indicate meningococcal septicaemia. Call 112/999 immediately. The 'glass test': press a clear glass on the rash — if it doesn't fade, it's an emergency."
            },
            {
                "question": "Sudden loss of vision in one eye, even if it returns (amaurosis fugax), should be:",
                "options": {
                    "A": "Monitored at home for a week",
                    "B": "Treated as a TIA (mini-stroke) warning and evaluated urgently",
                    "C": "Attributed to tiredness — rest your eyes",
                    "D": "Only concerning if it lasts more than an hour"
                },
                "correct": "B",
                "explanation": "Transient loss of vision in one eye (amaurosis fugax) is often a TIA warning sign — an early signal of impending stroke. Urgent evaluation within hours (not days) can prevent a full stroke."
            },
            {
                "question": "Increased thirst, frequent urination, unexplained weight loss, and blurred vision together may suggest:",
                "options": {
                    "A": "Normal aging",
                    "B": "Stress and dehydration",
                    "C": "Undiagnosed diabetes",
                    "D": "Kidney stones"
                },
                "correct": "C",
                "explanation": "These are the classic symptoms of undiagnosed diabetes — the '4 T's': Tired, Thirsty, Toilet (frequent urination), and Thinner (weight loss). A simple blood test can diagnose it."
            },
            {
                "question": "You should seek immediate help if a fever in an adult is above:",
                "options": {
                    "A": "37.5°C (99.5°F)",
                    "B": "38.0°C (100.4°F)",
                    "C": "39.0°C (102.2°F)",
                    "D": "40°C (104°F) or higher — especially with stiff neck, confusion, or rash"
                },
                "correct": "D",
                "explanation": "A fever above 40°C combined with stiff neck, confusion, sensitivity to light, or a non-blanching rash suggests serious infection (e.g., meningitis) requiring emergency care. High fever alone warrants urgent medical attention."
            },
        ],
    },
    {
        "slug": "pet-health-basics",
        "title": "Pet Health Basics",
        "description": "Is your furry friend trying to tell you something? Test your knowledge of common pet health signs — for every dog and cat owner.",
        "category": "veterinary",
        "questions": [
            {
                "question": "Which of these foods is toxic to dogs?",
                "options": {
                    "A": "Plain cooked chicken",
                    "B": "Carrots",
                    "C": "Grapes and raisins",
                    "D": "Plain rice"
                },
                "correct": "C",
                "explanation": "Grapes and raisins can cause sudden kidney failure in dogs — even a small amount can be fatal. Other toxic foods include chocolate, onions, xylitol (sweetener), macadamia nuts, and avocado."
            },
            {
                "question": "A cat that suddenly stops eating and becomes lethargic for more than 24 hours should be:",
                "options": {
                    "A": "Left alone — cats are naturally fussy eaters",
                    "B": "Given a different food to try",
                    "C": "Seen by a vet — prolonged anorexia in cats can cause liver disease",
                    "D": "Given human pain medication"
                },
                "correct": "C",
                "explanation": "Cats that stop eating for 24–48 hours can develop hepatic lipidosis (fatty liver disease). This is serious. Never give cats human pain medication — paracetamol is lethal to cats."
            },
            {
                "question": "How often should an adult dog typically be vaccinated against core diseases?",
                "options": {
                    "A": "Once in their lifetime",
                    "B": "Every month",
                    "C": "Every 1–3 years, depending on the vaccine and local requirements",
                    "D": "Only if they show signs of illness"
                },
                "correct": "C",
                "explanation": "Core vaccines (distemper, parvo, hepatitis, rabies) are given as puppies, then boostered every 1–3 years depending on the specific vaccine. Your vet will advise the right schedule."
            },
            {
                "question": "A dog is limping on a front leg after playing. You should:",
                "options": {
                    "A": "Give them human ibuprofen",
                    "B": "Rest them, apply a cold pack, and see a vet if it persists >24h",
                    "C": "Exercise them through it",
                    "D": "Give them aspirin — it's safe for dogs"
                },
                "correct": "B",
                "explanation": "Ibuprofen and most human pain medications are toxic to dogs. Rest and cold compresses are safe first aid. See a vet if the limp persists or the dog won't bear weight."
            },
            {
                "question": "Which of these is a sign of heatstroke in a dog?",
                "options": {
                    "A": "Slow, shallow breathing",
                    "B": "Excessive panting, drooling, bright red gums, and collapse",
                    "C": "Shivering and pale gums",
                    "D": "Quiet and sleepy behaviour"
                },
                "correct": "B",
                "explanation": "Heatstroke symptoms: excessive panting, thick drooling, red gums, vomiting, and collapse. Move to a cool area, apply cool (not ice cold) water to the skin, and get to a vet immediately — heatstroke kills quickly."
            },
            {
                "question": "Chocolate is dangerous to dogs because it contains:",
                "options": {
                    "A": "Too much sugar",
                    "B": "Theobromine and caffeine, which dogs cannot metabolise",
                    "C": "Lactose, which causes upset stomach",
                    "D": "Artificial sweeteners"
                },
                "correct": "B",
                "explanation": "Chocolate contains theobromine and caffeine. Dogs metabolise these substances much more slowly than humans. Dark chocolate and baking chocolate are the most dangerous. Even small amounts can cause vomiting, seizures, and death."
            },
            {
                "question": "At what age should kittens typically be neutered/spayed?",
                "options": {
                    "A": "1–2 weeks",
                    "B": "Around 4–6 months (before first heat cycle)",
                    "C": "Only after their first litter",
                    "D": "At 1 year old"
                },
                "correct": "B",
                "explanation": "Most vets recommend spaying/neutering cats around 4–6 months of age, before the first heat cycle. Early neutering reduces the risk of certain cancers and prevents unwanted litters."
            },
            {
                "question": "Your dog is vomiting persistently and the vomit contains blood. You should:",
                "options": {
                    "A": "Withhold food for 24 hours and monitor",
                    "B": "Give them antacids from your medicine cabinet",
                    "C": "Take them to a vet immediately",
                    "D": "Give them milk to coat the stomach"
                },
                "correct": "C",
                "explanation": "Blood in vomit is always a serious sign requiring immediate veterinary attention. It can indicate stomach ulcers, foreign body ingestion, poisoning, or other emergencies."
            },
        ],
    },
    {
        "slug": "human-anatomy-for-everyone",
        "title": "Human Anatomy for Everyone",
        "description": "How well do you know the machine you live in? A fun anatomy quiz for the curious — no biology degree needed.",
        "category": "anatomy",
        "questions": [
            {
                "question": "The heart has how many chambers?",
                "options": {
                    "A": "2",
                    "B": "3",
                    "C": "4",
                    "D": "6"
                },
                "correct": "C",
                "explanation": "The heart has 4 chambers: right atrium, right ventricle, left atrium, and left ventricle. The right side pumps blood to the lungs; the left side pumps it to the rest of the body."
            },
            {
                "question": "Which organ filters about 180 litres of blood per day, producing urine?",
                "options": {
                    "A": "Liver",
                    "B": "Kidneys",
                    "C": "Spleen",
                    "D": "Pancreas"
                },
                "correct": "B",
                "explanation": "Your two kidneys filter approximately 180 litres of blood every day, producing about 1–2 litres of urine. They regulate blood pressure, fluid balance, and electrolytes."
            },
            {
                "question": "The largest organ of the human body is:",
                "options": {
                    "A": "The liver",
                    "B": "The lungs",
                    "C": "The skin",
                    "D": "The brain"
                },
                "correct": "C",
                "explanation": "The skin is the largest organ — in adults it covers about 1.7–2.0 m² and weighs around 4–5 kg. It protects against infection, regulates temperature, and provides sensory information."
            },
            {
                "question": "Which part of the brain controls balance and coordination?",
                "options": {
                    "A": "Frontal lobe",
                    "B": "Hippocampus",
                    "C": "Cerebellum",
                    "D": "Amygdala"
                },
                "correct": "C",
                "explanation": "The cerebellum ('little brain') at the back of the skull coordinates movement, balance, and fine motor skills. Damage to it causes ataxia — unsteady, staggering movement."
            },
            {
                "question": "Red blood cells carry oxygen because they contain:",
                "options": {
                    "A": "Chlorophyll",
                    "B": "Haemoglobin — an iron-containing protein",
                    "C": "White cells",
                    "D": "ATP molecules"
                },
                "correct": "B",
                "explanation": "Haemoglobin is a protein in red blood cells that contains iron. Iron binds to oxygen in the lungs and releases it to tissues throughout the body. Low haemoglobin = anaemia."
            },
            {
                "question": "The longest bone in the human body is:",
                "options": {
                    "A": "The spine",
                    "B": "The humerus (upper arm)",
                    "C": "The femur (thigh bone)",
                    "D": "The tibia (shin)"
                },
                "correct": "C",
                "explanation": "The femur (thigh bone) is the longest and strongest bone, typically about 25–28% of a person's height. It connects the hip to the knee and supports all your body weight when standing."
            },
            {
                "question": "How many bones does an adult human body have?",
                "options": {
                    "A": "106",
                    "B": "206",
                    "C": "306",
                    "D": "Babies and adults have the same number"
                },
                "correct": "B",
                "explanation": "Adults have 206 bones. Babies are born with about 270–300 smaller bones that fuse as they grow. By young adulthood the skeleton stabilises at 206."
            },
            {
                "question": "The appendix is part of which body system?",
                "options": {
                    "A": "Nervous system",
                    "B": "Respiratory system",
                    "C": "Digestive system",
                    "D": "Endocrine system"
                },
                "correct": "C",
                "explanation": "The appendix is a small pouch attached to the large intestine (digestive system). Its function is debated — it may play a role in gut immunity. Appendicitis (inflammation) is one of the most common surgical emergencies."
            },
            {
                "question": "Blood pressure reading of '120/80 mmHg' means:",
                "options": {
                    "A": "120 is the resting heart rate, 80 is the oxygen level",
                    "B": "120 is systolic (heart contracting), 80 is diastolic (heart relaxing) pressure",
                    "C": "120 mg of sodium per 80 ml of blood",
                    "D": "Both numbers indicate blood sugar"
                },
                "correct": "B",
                "explanation": "Systolic (top number) is the pressure when your heart beats. Diastolic (bottom number) is the pressure between beats. 120/80 is considered normal; 140/90+ is hypertension (high blood pressure)."
            },
            {
                "question": "The small intestine is responsible for:",
                "options": {
                    "A": "Producing digestive enzymes only",
                    "B": "Absorbing most nutrients from food into the bloodstream",
                    "C": "Storing waste before excretion",
                    "D": "Producing bile for fat digestion"
                },
                "correct": "B",
                "explanation": "The small intestine (about 6–7 metres long) is where most digestion and nutrient absorption happens. Its lining is covered in tiny finger-like projections (villi) that massively increase surface area for absorption."
            },
        ],
    },
]


async def seed():
    async with AsyncSessionLocal() as db:
        for quiz_data in QUIZZES:
            existing = await db.execute(
                select(PublicQuiz).where(PublicQuiz.slug == quiz_data["slug"])
            )
            if existing.scalar_one_or_none():
                continue  # Already seeded
            db.add(PublicQuiz(
                id=uuid.uuid4(),
                **quiz_data,
            ))
        await db.commit()


if __name__ == "__main__":
    asyncio.run(seed())
