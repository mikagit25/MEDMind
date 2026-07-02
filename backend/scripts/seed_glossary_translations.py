"""Seed lay_glossary translations for all 9 vet lessons × 5 non-EN non-RU locales."""
import asyncio
import json
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

# lesson_id → locale → [{term, simple_definition}]
TRANSLATIONS: dict[str, dict[str, list]] = {

    # ── Dog red flags ──────────────────────────────────────────────────────────
    "bec411e7-7589-4bc9-b83a-5cd92734806e": {
        "de": [
            {"term": "GDV (Magendrehung)",
             "simple_definition": "Lebensbedrohlicher Zustand, bei dem sich der Magen mit Gas füllt und verdreht, die Blutversorgung unterbricht. Erfordert eine Notoperation — Hunde können ohne Behandlung innerhalb von Stunden sterben."},
            {"term": "Krampfanfall",
             "simple_definition": "Plötzliche unkontrollierte elektrische Aktivität im Gehirn, die Muskelkrämpfe oder Bewusstlosigkeit verursacht. Kurze Anfälle (unter 2 Minuten) sind weniger gefährlich als lang anhaltende."},
            {"term": "Blasses oder graues Zahnfleisch",
             "simple_definition": "Zeichen, dass nicht genug Blut oder Sauerstoff das Gewebe erreicht. Normales Hundzahnfleisch ist kaugummifarben rosa. Blasses, weißes oder graues Zahnfleisch signalisiert einen ernsthaften Notfall."},
        ],
        "fr": [
            {"term": "Dilatation-volvulus gastrique (DVG)",
             "simple_definition": "Affection mettant en jeu le pronostic vital où l'estomac se dilate et se tord, coupant l'apport sanguin. Nécessite une chirurgie d'urgence — les chiens peuvent mourir en quelques heures sans traitement."},
            {"term": "Convulsion",
             "simple_definition": "Épisode soudain d'activité électrique incontrôlée dans le cerveau, provoquant des convulsions musculaires ou une perte de conscience. Les convulsions brèves (moins de 2 minutes) sont moins dangereuses que les prolongées."},
            {"term": "Gencives pâles ou grises",
             "simple_definition": "Signe d'un apport insuffisant de sang ou d'oxygène aux tissus. Les gencives normales d'un chien sont rose vif. Des gencives pâles, blanches ou grises signalent une urgence grave."},
        ],
        "es": [
            {"term": "Dilatación-vólvulo gástrico (DVG)",
             "simple_definition": "Afección potencialmente mortal donde el estómago se llena de gas y gira sobre sí mismo, cortando el suministro de sangre. Requiere cirugía de emergencia — los perros pueden morir en horas sin tratamiento."},
            {"term": "Convulsión",
             "simple_definition": "Episodio repentino de actividad eléctrica incontrolada en el cerebro que causa convulsiones musculares o pérdida de conciencia. Las convulsiones breves (menos de 2 minutos) son menos peligrosas."},
            {"term": "Encías pálidas o grises",
             "simple_definition": "Señal de que no llega suficiente sangre u oxígeno a los tejidos. Las encías normales de un perro son de color rosa chicle. Las encías pálidas, blancas o grises indican una emergencia grave."},
        ],
        "tr": [
            {"term": "Gastrik Dilatasyon-Volvulus (GDV)",
             "simple_definition": "Midenin gazla dolup burkulduğu ve kan akışını kestiği hayatı tehdit eden durum. Acil ameliyat gerektirir — tedavi yapılmazsa köpekler saatler içinde ölebilir."},
            {"term": "Nöbet",
             "simple_definition": "Beyinde ani kontrolsüz elektrik aktivitesi sonucu kas krampları veya bilinç kaybı yaşanması. Kısa nöbetler (2 dakikanın altında) uzun sürelilerden daha az tehlikelidir."},
            {"term": "Soluk veya gri diş etleri",
             "simple_definition": "Dokulara yeterli kan veya oksijen ulaşmadığının işareti. Normal köpek diş etleri pembe renktedir. Soluk, beyaz veya gri diş etleri ciddi bir acil duruma işaret eder."},
        ],
        "ar": [
            {"term": "توسع المعدة والتواؤها (GDV)",
             "simple_definition": "حالة تهدد الحياة يمتلئ فيها المعدة بالغاز وتلتوي قاطعةً الإمداد الدموي. تتطلب جراحة طارئة — قد يموت الكلب في غضون ساعات دون علاج."},
            {"term": "النوبة التشنجية",
             "simple_definition": "نشاط كهربائي مفاجئ وغير منضبط في الدماغ يسبب تشنجات عضلية أو فقدان الوعي. النوبات القصيرة (أقل من دقيقتين) أقل خطورة من الطويلة."},
            {"term": "اللثة الشاحبة أو الرمادية",
             "simple_definition": "علامة على عدم وصول كمية كافية من الدم أو الأكسجين إلى الأنسجة. لثة الكلب الطبيعية وردية اللون. اللثة الشاحبة أو البيضاء أو الرمادية تشير إلى حالة طارئة خطيرة."},
        ],
    },

    # ── Cat red flags ──────────────────────────────────────────────────────────
    "0a404383-e932-4754-989a-b2d80818c043": {
        "de": [
            {"term": "Harnröhrenobstruktion",
             "simple_definition": "Blockade des Harnröhrenkanals. Bei Katern ist die Harnröhre sehr eng und wird leicht durch Kristalle oder Schleimpfropfen blockiert. Ohne Behandlung können Toxine im Blut lebensbedrohlich werden."},
            {"term": "Aortenthromboembolie (Sattelthrombus)",
             "simple_definition": "Blutgerinnsel an der Basis der Hauptschlagader, das den Blutfluss in die Hinterbeine unterbricht. Verursacht plötzliche Lähmung und starke Schmerzen. Mit einer Herzerkrankung verbunden."},
            {"term": "Hepatische Lipidose",
             "simple_definition": "Fettlebererkrankung, die entsteht, wenn eine Katze einige Tage lang nicht frisst. Fett gelangt schneller in die Leber als es verarbeitet werden kann, was zu Leberversagen führt."},
        ],
        "fr": [
            {"term": "Obstruction urétrale",
             "simple_definition": "Blocage du tube évacuant l'urine. Chez les chats mâles, l'urètre est très étroit et facilement bouché par des cristaux. Sans traitement, les toxines s'accumulent dans le sang et menacent la vie."},
            {"term": "Thromboembolie aortique (thrombus en selle)",
             "simple_definition": "Caillot sanguin à la base de l'aorte coupant la circulation vers les pattes postérieures. Provoque une paralysie soudaine et une douleur intense. Associé à une maladie cardiaque sous-jacente."},
            {"term": "Lipidose hépatique",
             "simple_definition": "Maladie du foie gras qui se développe quand un chat cesse de manger quelques jours. Les graisses s'accumulent dans le foie plus vite qu'elles ne sont métabolisées, causant une insuffisance hépatique."},
        ],
        "es": [
            {"term": "Obstrucción uretral",
             "simple_definition": "Bloqueo del tubo por el que sale la orina. En los gatos machos, la uretra es muy estrecha y se bloquea fácilmente con cristales. Sin tratamiento, las toxinas se acumulan en sangre poniendo en riesgo la vida."},
            {"term": "Tromboembolia aórtica (trombo en silla de montar)",
             "simple_definition": "Coágulo de sangre en la base de la aorta que corta el flujo hacia las patas traseras. Causa parálisis repentina y dolor intenso. Asociado a enfermedad cardíaca subyacente."},
            {"term": "Lipidosis hepática",
             "simple_definition": "Enfermedad del hígado graso que se desarrolla cuando un gato deja de comer. La grasa se acumula en el hígado más rápido de lo que puede procesarse, causando insuficiencia hepática."},
        ],
        "tr": [
            {"term": "Üretral tıkanıklık",
             "simple_definition": "İdrara çıkma kanalının tıkanması. Erkek kedilerde üretra çok dardır ve kristallerle kolayca tıkanabilir. Tedavi yapılmazsa toksinler kanda birikir ve hayatı tehdit eder."},
            {"term": "Aortik tromboembolizm (eyer trombusu)",
             "simple_definition": "Arka bacaklara giden ana damarın dibinde kan pıhtısı oluşarak kan akışını kesmesi. Ani felç ve şiddetli ağrıya neden olur. Kalp hastalığıyla ilişkilidir."},
            {"term": "Hepatik lipidoz",
             "simple_definition": "Kedi birkaç gün yemek yemediğinde gelişen karaciğer yağlanması hastalığı. Yağ, işlenebileceğinden daha hızlı birikir ve karaciğer yetmezliğine yol açar."},
        ],
        "ar": [
            {"term": "انسداد مجرى البول",
             "simple_definition": "انسداد الأنبوب الذي يحمل البول. في القطط الذكور يكون مجرى البول ضيقاً جداً ويسد بسهولة بالبلورات. بدون علاج تتراكم السموم في الدم مهددةً الحياة."},
            {"term": "الانصمام الخثاري الأبهري (الخثرة الرُّكوبية)",
             "simple_definition": "جلطة دموية في قاعدة الشريان الأبهر تقطع تدفق الدم إلى الأرجل الخلفية. يسبب شللاً مفاجئاً وألماً شديداً. مرتبط بمرض قلبي كامن."},
            {"term": "التنكس الدهني الكبدي",
             "simple_definition": "مرض يصيب الكبد عندما تتوقف القطة عن الأكل حتى لأيام قليلة. تتراكم الدهون في الكبد أسرع مما يمكن معالجته مسببةً قصوراً كبدياً."},
        ],
    },

    # ── Dog foods ──────────────────────────────────────────────────────────────
    "6c87adb8-3a11-418b-85ba-bf82d9c66c8e": {
        "de": [
            {"term": "Theobromin",
             "simple_definition": "Eine natürlich in Schokolade vorkommende chemische Substanz, die Hunde nicht abbauen können — sie reichert sich im Körper an und wird toxisch."},
            {"term": "Xylitol",
             "simple_definition": "Ein Zuckerersatz in vielen zuckerfreien Produkten. Äußerst gefährlich für Hunde — verursacht einen plötzlichen, gefährlichen Abfall des Blutzuckerspiegels."},
            {"term": "Anämie",
             "simple_definition": "Zustand, bei dem nicht genügend gesunde rote Blutkörperchen vorhanden sind, um Sauerstoff im Körper zu transportieren, was zu Schwäche und blassem Zahnfleisch führt."},
        ],
        "fr": [
            {"term": "Théobromine",
             "simple_definition": "Substance chimique naturellement présente dans le chocolat que les chiens ne peuvent pas métaboliser — elle s'accumule dans leur organisme et devient toxique."},
            {"term": "Xylitol",
             "simple_definition": "Édulcorant utilisé dans de nombreux produits sans sucre. Extrêmement dangereux pour les chiens — provoque une chute soudaine et dangereuse de la glycémie."},
            {"term": "Anémie",
             "simple_definition": "État dans lequel il n'y a pas assez de globules rouges sains pour transporter l'oxygène dans le corps, causant faiblesse et pâleur des gencives."},
        ],
        "es": [
            {"term": "Teobromina",
             "simple_definition": "Sustancia química presente de forma natural en el chocolate que los perros no pueden metabolizar — se acumula en su organismo y se vuelve tóxica."},
            {"term": "Xilitol",
             "simple_definition": "Sustituto del azúcar en muchos productos sin azúcar. Extremadamente peligroso para los perros — provoca una bajada repentina y peligrosa del azúcar en sangre."},
            {"term": "Anemia",
             "simple_definition": "Condición donde no hay suficientes glóbulos rojos saludables para transportar oxígeno, causando debilidad y palidez de las encías."},
        ],
        "tr": [
            {"term": "Teobromin",
             "simple_definition": "Çikolatada doğal olarak bulunan ve köpeklerin metabolize edemediği kimyasal madde — vücutta birikir ve toksik hale gelir."},
            {"term": "Ksilitol",
             "simple_definition": "Şekersiz ürünlerde kullanılan tatlandırıcı. Köpekler için son derece tehlikelidir — ani ve tehlikeli kan şekeri düşüşüne neden olur."},
            {"term": "Anemi",
             "simple_definition": "Vücutta oksijen taşımak için yeterli sağlıklı kırmızı kan hücresi bulunmaması durumu; güçsüzlük ve soluk diş etlerine yol açar."},
        ],
        "ar": [
            {"term": "الثيوبرومين",
             "simple_definition": "مادة كيميائية موجودة طبيعياً في الشوكولاتة لا يستطيع الكلب تحليلها — تتراكم في جسمه وتصبح سامة."},
            {"term": "الكسيليتول",
             "simple_definition": "بديل السكر في كثير من المنتجات الخالية من السكر. بالغ الخطورة على الكلاب — يسبب انخفاضاً حاداً وخطيراً في سكر الدم."},
            {"term": "فقر الدم",
             "simple_definition": "حالة تكون فيها خلايا الدم الحمراء غير كافية لنقل الأكسجين في الجسم مما يسبب الضعف وشحوب اللثة."},
        ],
    },

    # ── Cat foods ──────────────────────────────────────────────────────────────
    "734522de-d457-44af-8ce9-81d59484406d": {
        "de": [
            {"term": "Obligater Fleischfresser",
             "simple_definition": "Tier, das zum Überleben Fleisch fressen muss — sein Körper kann bestimmte Nährstoffe nicht aus Pflanzen synthetisieren."},
            {"term": "Taurin",
             "simple_definition": "Aminosäure, die Katzen nicht selbst herstellen können und über die Nahrung aufnehmen müssen. Mangel verursacht Herzerkrankungen und Blindheit bei Katzen."},
            {"term": "Liliengiftigkeit",
             "simple_definition": "Schon kleinste Mengen echter Liliengewächse verursachen akutes Nierenversagen bei Katzen — oft tödlich ohne sofortige Behandlung innerhalb von 6 Stunden."},
        ],
        "fr": [
            {"term": "Carnivore strict",
             "simple_definition": "Animal qui doit manger de la viande pour survivre — son organisme ne peut pas synthétiser certains nutriments à partir des plantes."},
            {"term": "Taurine",
             "simple_definition": "Acide aminé que les chats ne peuvent pas fabriquer eux-mêmes et doivent obtenir via l'alimentation. Une carence provoque des maladies cardiaques et la cécité chez les chats."},
            {"term": "Toxicité des lis",
             "simple_definition": "Même de minuscules quantités de vraies plantes lis provoquent une insuffisance rénale aiguë chez les chats — souvent fatale sans traitement immédiat dans les 6 heures."},
        ],
        "es": [
            {"term": "Carnívoro estricto",
             "simple_definition": "Animal que debe comer carne para sobrevivir — su organismo no puede sintetizar ciertos nutrientes a partir de plantas."},
            {"term": "Taurina",
             "simple_definition": "Aminoácido que los gatos no pueden sintetizar por sí mismos y deben obtener de la comida. Su deficiencia causa enfermedades cardíacas y ceguera en gatos."},
            {"term": "Toxicidad de los lirios",
             "simple_definition": "Incluso cantidades diminutas de plantas de lirio verdadero causan insuficiencia renal aguda en gatos — con frecuencia fatal sin tratamiento inmediato en 6 horas."},
        ],
        "tr": [
            {"term": "Zorunlu etçil",
             "simple_definition": "Hayatta kalmak için et yemek zorunda olan hayvan — vücudu bitkilerden belirli besinleri sentezleyemez."},
            {"term": "Taurin",
             "simple_definition": "Kedilerin kendileri üretemediği ve besinlerden almak zorunda olduğu amino asit. Eksikliği kedilerde kalp hastalığı ve körlüğe yol açar."},
            {"term": "Zambak toksisitesi",
             "simple_definition": "Gerçek zambak bitkilerinin en küçük miktarları bile kedilerde akut böbrek yetmezliğine neden olur — 6 saat içinde tedavi edilmezse genellikle ölümcüldür."},
        ],
        "ar": [
            {"term": "آكل اللحوم الإلزامي",
             "simple_definition": "حيوان يجب أن يأكل اللحوم للبقاء على قيد الحياة — جسمه لا يستطيع تصنيع مغذيات معينة من النباتات."},
            {"term": "التورين",
             "simple_definition": "حمض أميني لا تستطيع القطط تصنيعه بأنفسهن ويجب الحصول عليه من الغذاء. نقصه يسبب أمراض القلب والعمى في القطط."},
            {"term": "سمية نبات الزنبق",
             "simple_definition": "حتى الكميات الضئيلة من نباتات الزنبق تسبب فشلاً كلوياً حاداً في القطط — غالباً ما يكون مميتاً بدون علاج فوري خلال 6 ساعات."},
        ],
    },

    # ── Triage / CRT ───────────────────────────────────────────────────────────
    "1a7a6e67-156f-4184-a9a8-8894fac34bc8": {
        "de": [
            {"term": "Triage",
             "simple_definition": "Der Prozess, die Behandlungsdringlichkeit eines Patienten zu beurteilen. Notaufnahmen behandeln die kritischsten Tiere zuerst — daher kann ein 'normal aussehendes' Tier warten, während ein zusammengebrochenes sofort behandelt wird."},
            {"term": "Kapilläre Füllungszeit (KFZ)",
             "simple_definition": "Schneller Kreislauftest: Zahnfleisch des Tieres bis zur Weißfärbung drücken, loslassen und Sekunden bis zur Rückkehr der Rosafarbe zählen. Normal: unter 2 Sekunden. Länger deutet auf schlechte Durchblutung oder Schock hin."},
        ],
        "fr": [
            {"term": "Triage",
             "simple_definition": "Processus d'évaluation de l'urgence du traitement d'un patient. Les cliniques vétérinaires d'urgence voient d'abord les animaux les plus critiques — c'est pourquoi un animal qui 'semble bien' peut attendre."},
            {"term": "Temps de remplissage capillaire (TRC)",
             "simple_definition": "Test rapide de circulation : appuyer doucement sur la gencive jusqu'à ce qu'elle blanchisse, relâcher et compter les secondes avant le retour de la couleur rose. Normal : moins de 2 secondes. Plus long peut indiquer un choc."},
        ],
        "es": [
            {"term": "Triaje",
             "simple_definition": "Proceso de determinar la urgencia del tratamiento de un paciente. Las clínicas de emergencias veterinarias atienden primero a los animales más críticos — por eso un animal que 'parece bien' puede esperar."},
            {"term": "Tiempo de relleno capilar (TRC)",
             "simple_definition": "Test rápido de circulación: presionar suavemente la encía hasta que se ponga blanca, soltar y contar segundos hasta que vuelva el color rosa. Normal: menos de 2 segundos. Más tiempo puede indicar shock."},
        ],
        "tr": [
            {"term": "Triyaj",
             "simple_definition": "Bir hastanın tedavi aciliyetini belirleme süreci. Acil veteriner klinikleri önce en kritik hayvanları görür — bu nedenle 'iyi görünen' bir hayvan beklerken kollapstaki hayvan hemen tedavi edilir."},
            {"term": "Kılcal dolum zamanı (KDZ)",
             "simple_definition": "Hızlı dolaşım testi: dişetine beyazlayana kadar hafifçe basın, bırakın ve pembe rengin geri dönmesi için geçen süreyi sayın. Normal: 2 saniyenin altı. Daha uzun süre şoka işaret edebilir."},
        ],
        "ar": [
            {"term": "الفرز الطبي (ترياج)",
             "simple_definition": "عملية تحديد مدى إلحاحية علاج المريض. تستقبل عيادات الطوارئ البيطرية الحيوانات الأكثر خطورة أولاً — لذلك قد ينتظر الحيوان الذي يبدو بخير بينما يُعالَج المنهك فوراً."},
            {"term": "وقت امتلاء الشعيرات الدموية",
             "simple_definition": "اختبار سريع للدورة الدموية: اضغط برفق على اللثة حتى تبيض ثم أطلق واعدد الثواني حتى يعود اللون الوردي. الطبيعي: أقل من ثانيتين. أكثر من ذلك قد يشير إلى صدمة."},
        ],
    },

    # ── Household toxins ───────────────────────────────────────────────────────
    "7704af3b-f6a5-4682-a5e5-402cd992efa9": {
        "de": [
            {"term": "Antikoagulanzien-Rodentizid",
             "simple_definition": "Rattengifttyp, der die Blutgerinnung verhindert. Tiere, die es fressen (oder eine vergiftete Ratte), können innerlich verbluten — Symptome können erst Tage später auftreten."},
            {"term": "Ethylenglykol",
             "simple_definition": "Wirkstoff in Frostschutzmitteln. Schmeckt süß und ist extrem giftig — verursacht innerhalb von Stunden irreversibles Nierenversagen ohne sofortige Behandlung."},
            {"term": "Metaldehyd",
             "simple_definition": "Wirkstoff in den meisten Schneckenmitteln. Verursacht bei Tieren starke Muskelkrämpfe — schon wenige Pellets können tödlich sein."},
        ],
        "fr": [
            {"term": "Rodenticide anticoagulant",
             "simple_definition": "Type de poison pour rongeurs qui empêche la coagulation du sang. Les animaux qui l'ingèrent peuvent mourir d'hémorragie interne — les symptômes peuvent n'apparaître que plusieurs jours plus tard."},
            {"term": "Éthylène glycol",
             "simple_definition": "Principe actif de l'antigel. Au goût sucré et extrêmement toxique — provoque une insuffisance rénale irréversible en quelques heures sans traitement immédiat."},
            {"term": "Métaldéhyde",
             "simple_definition": "Principe actif de la plupart des granulés anti-limaces. Provoque de violentes convulsions musculaires chez les animaux — même quelques granulés peuvent être mortels."},
        ],
        "es": [
            {"term": "Rodenticida anticoagulante",
             "simple_definition": "Tipo de veneno para roedores que impide la coagulación de la sangre. Los animales que lo ingieren pueden morir de hemorragia interna — los síntomas pueden tardar varios días en aparecer."},
            {"term": "Etilenglicol",
             "simple_definition": "Ingrediente activo del anticongelante. De sabor dulce y extremadamente tóxico — causa insuficiencia renal irreversible en pocas horas sin tratamiento inmediato."},
            {"term": "Metaldehído",
             "simple_definition": "Ingrediente activo de la mayoría de los cebos para babosas. Causa fuertes convulsiones musculares en los animales — incluso pocos gránulos pueden ser mortales."},
        ],
        "tr": [
            {"term": "Antikoagülan rodentisit",
             "simple_definition": "Kanın pıhtılaşmasını önleyen fare zehiri türü. Yiyen hayvanlar iç kanama ile ölebilir — belirtiler günlerce sonra ortaya çıkabilir."},
            {"term": "Etilen glikol",
             "simple_definition": "Antifrizin aktif bileşeni. Tatlı bir tada sahiptir ve son derece zehirlidir — hemen tedavi edilmezse saatler içinde geri dönüşümsüz böbrek yetmezliğine neden olur."},
            {"term": "Metaldehit",
             "simple_definition": "Salyangoz ve sümüklü böcek granüllerinin aktif bileşeni. Hayvanlarda şiddetli kas kramplarına neden olur — birkaç granül bile ölümcül olabilir."},
        ],
        "ar": [
            {"term": "مبيد القوارض المضاد للتخثر",
             "simple_definition": "نوع من سم الفئران يمنع تخثر الدم. الحيوانات التي تتناوله قد تنزف داخلياً حتى الموت — قد لا تظهر الأعراض إلا بعد أيام."},
            {"term": "الإيثيلين جلايكول",
             "simple_definition": "المكوّن الفعّال في سائل مانع التجمد. طعمه حلو وشديد السمية — يسبب فشلاً كلوياً لا رجعة فيه خلال ساعات بدون علاج فوري."},
            {"term": "الميتالديهايد",
             "simple_definition": "المكوّن الفعّال في معظم مبيدات القواقع. يسبب تشنجات عضلية شديدة في الحيوانات — حتى بضع حبيبات قد تكون مميتة."},
        ],
    },

    # ── Vaccination ────────────────────────────────────────────────────────────
    "6617737d-f744-45a4-a01b-6c484c9bb186": {
        "de": [
            {"term": "Pflichtimpfstoff",
             "simple_definition": "Impfung, die für jedes Tier dieser Spezies empfohlen wird, unabhängig von Lebensstil oder Standort — weil die Krankheit schwerwiegend, weit verbreitet oder auf Menschen übertragbar ist."},
            {"term": "Auffrischungsimpfung",
             "simple_definition": "Nachfolgeimpfung nach dem ersten Kurs, um das Immunsystem zu erinnern und den Schutz im Laufe der Zeit aufrechtzuerhalten."},
            {"term": "Parvovirus",
             "simple_definition": "Hochansteckender und oft tödlicher Virus bei Hunden und Katzen. Greift schnell teilende Zellen an — Darmschleimhaut und Knochenmark — und verursacht schweres Erbrechen, blutige Durchfälle und Immunzusammenbruch. Impfbar."},
        ],
        "fr": [
            {"term": "Vaccin essentiel",
             "simple_definition": "Vaccin recommandé à tout animal de cette espèce, quel que soit son mode de vie, car la maladie est grave, répandue ou transmissible à l'homme."},
            {"term": "Rappel vaccinal",
             "simple_definition": "Vaccin de suivi administré après la série initiale pour rappeler au système immunitaire de maintenir la protection dans le temps."},
            {"term": "Parvovirus",
             "simple_definition": "Virus hautement contagieux et souvent mortel chez les chiens et les chats. Il attaque les cellules à division rapide — la muqueuse intestinale et la moelle osseuse — provoquant vomissements sévères, diarrhée sanglante et effondrement immunitaire. Évitable par vaccination."},
        ],
        "es": [
            {"term": "Vacuna básica",
             "simple_definition": "Vacuna recomendada para todo animal de esa especie, independientemente de su estilo de vida, porque la enfermedad es grave, extendida o transmisible a personas."},
            {"term": "Refuerzo",
             "simple_definition": "Vacuna de seguimiento tras la serie inicial para recordar al sistema inmunitario y mantener la protección a lo largo del tiempo."},
            {"term": "Parvovirus",
             "simple_definition": "Virus altamente contagioso y a menudo mortal en perros y gatos. Ataca las células de división rápida — intestino y médula ósea — causando vómitos graves, diarrea con sangre y colapso inmune. Prevenible con vacuna."},
        ],
        "tr": [
            {"term": "Temel aşı",
             "simple_definition": "Yaşam tarzı veya konumdan bağımsız olarak o türün her hayvanına önerilen aşı — hastalık ciddi, yaygın veya insanlara bulaşabildiği için."},
            {"term": "Hatırlatma aşısı",
             "simple_definition": "Bağışıklık sistemini hatırlatmak ve zamanla korumayı sürdürmek için ilk seri tamamlandıktan sonra yapılan takip aşısı."},
            {"term": "Parvovirus",
             "simple_definition": "Köpek ve kedilerde yüksek oranda bulaşıcı ve sıklıkla ölümcül virüs. Hızlı bölünen hücrelere saldırır — bağırsak mukozası ve kemik iliği — şiddetli kusma, kanlı ishal ve bağışıklık çöküşüne neden olur. Aşıyla önlenebilir."},
        ],
        "ar": [
            {"term": "اللقاح الأساسي",
             "simple_definition": "لقاح يُوصى به لكل حيوان من هذا النوع بصرف النظر عن نمط حياته لأن المرض خطير أو منتشر أو قابل للانتقال للإنسان."},
            {"term": "الجرعة المنشطة",
             "simple_definition": "لقاح لاحق يُعطى بعد الدورة الأولى لتذكير الجهاز المناعي والحفاظ على الحماية مع مرور الوقت."},
            {"term": "فيروس البارفو",
             "simple_definition": "فيروس شديد العدوى وغالباً مميت في الكلاب والقطط. يهاجم الخلايا سريعة الانقسام — بطانة الأمعاء ونخاع العظم — مسبباً قياءً شديداً وإسهالاً دموياً وانهياراً مناعياً. يمكن الوقاية منه بالتطعيم."},
        ],
    },

    # ── Parasites ──────────────────────────────────────────────────────────────
    "4009cb77-549a-4eaf-91a3-34ad15a8cc2c": {
        "de": [
            {"term": "Herzwurm (Dirofilaria immitis)",
             "simple_definition": "Parasitischer Wurm, der durch Mückenstiche übertragen wird und in Herz und Lunge infizierter Tiere lebt. Kann tödliche Herzschäden verursachen. Vorbeugung ist hochwirksam."},
            {"term": "Durch Zecken übertragene Krankheit",
             "simple_definition": "Krankheit, die durch den Stich einer infizierten Zecke übertragen wird: Lyme-Borreliose, Ehrlichiose, Anaplasmose, Babesiose u.a. Einige betreffen sowohl Tiere als auch Menschen."},
            {"term": "Zoonose",
             "simple_definition": "Krankheit, die zwischen Tieren und Menschen übertragen werden kann. Einige Parasiten von Haustieren (Spulwürmer, Toxoplasmose, Ringelflechte) sind für Menschen gefährlich — besonders Kinder und Immungeschwächte."},
        ],
        "fr": [
            {"term": "Ver du cœur (Dirofilaria immitis)",
             "simple_definition": "Ver parasite transmis par les moustiques vivant dans le cœur et les poumons des animaux infectés. Peut provoquer des lésions cardio-pulmonaires mortelles. La prévention est très efficace."},
            {"term": "Maladie transmise par les tiques",
             "simple_definition": "Maladie transmise par la piqûre d'une tique infectée : maladie de Lyme, ehrlichiose, anaplasmose, babésiose, etc. Certaines touchent à la fois les animaux et les humains."},
            {"term": "Zoonose",
             "simple_definition": "Maladie pouvant se propager entre animaux et humains. Certains parasites d'animaux de compagnie (ascaris, toxoplasmose, teigne) sont dangereux pour les personnes — surtout les enfants et les immunodéprimés."},
        ],
        "es": [
            {"term": "Gusano del corazón (Dirofilaria immitis)",
             "simple_definition": "Gusano parásito transmitido por mosquitos que vive en el corazón y los pulmones de los animales infectados. Puede causar daños cardiopulmonares mortales. La prevención es muy eficaz."},
            {"term": "Enfermedad transmitida por garrapatas",
             "simple_definition": "Enfermedad transmitida por la picadura de una garrapata infectada: enfermedad de Lyme, ehrlichiosis, anaplasmosis, babesiosis, entre otras. Algunas afectan tanto a animales como a humanos."},
            {"term": "Zoonosis",
             "simple_definition": "Enfermedad que puede propagarse entre animales y humanos. Algunos parásitos de mascotas (ascaris, toxoplasma, tiña) son peligrosos para las personas — especialmente niños e inmunodeprimidos."},
        ],
        "tr": [
            {"term": "Kalp kurdu (Dirofilaria immitis)",
             "simple_definition": "Sivrisinekler aracılığıyla bulaşan ve enfekte hayvanların kalp ile akciğerlerinde yaşayan parazit kurt. Ölümcül kalp-akciğer hasarına neden olabilir. Korunma son derece etkilidir."},
            {"term": "Keneden bulaşan hastalık",
             "simple_definition": "Enfekte bir kenenin ısırmasıyla bulaşan hastalık: Lyme hastalığı, ehrlichiosis, anaplasmoz, babesioz vb. Bazıları hem hayvanları hem de insanları etkiler."},
            {"term": "Zoonoz",
             "simple_definition": "Hayvanlar ile insanlar arasında bulaşabilen hastalık. Bazı evcil hayvan parazitleri (bağırsak kurdu, toksoplazmoz, saçkıran) insanlar için tehlikelidir — özellikle çocuklar ve bağışıklığı zayıf kişiler."},
        ],
        "ar": [
            {"term": "دودة القلب (Dirofilaria immitis)",
             "simple_definition": "دودة طفيلية تنتقل عبر لدغات البعوض وتعيش في قلب ورئتي الحيوانات المصابة. يمكن أن تسبب تلفاً قاتلاً في القلب والرئتين. الوقاية منها فعّالة للغاية."},
            {"term": "الأمراض المنقولة بالقراد",
             "simple_definition": "أمراض تنتقل عبر لدغة قراد مصاب: داء لايم والإيرليخيا وداء الأنابلازما والبابيزيا وغيرها. بعضها يصيب الحيوانات والإنسان معاً."},
            {"term": "الزونوز (الأمراض الحيوانية المنشأ)",
             "simple_definition": "مرض يمكن أن ينتقل بين الحيوانات والإنسان. بعض طفيليات الحيوانات الأليفة (الديدان الأسطوانية وداء المقوسات والسعفة) خطرة على الإنسان — خاصة الأطفال وضعاف المناعة."},
        ],
    },

    # ── Dental health ──────────────────────────────────────────────────────────
    "765060b0-1cdb-4888-b2e0-9319435f4a72": {
        "de": [
            {"term": "Parodontitis",
             "simple_definition": "Infektion und Zerstörung der Zahnhaltestrukturen — Zahnfleisch, Parodontium und Kieferknochen. Beginnt mit Plaque, schreitet zu Zahnstein fort, dann Zahnfleischentzündung und Knochenverlust."},
            {"term": "Zahnstein (Zahnkonkrement)",
             "simple_definition": "Mineralisierter Zahnbelag auf der Zahnoberfläche. Einmal gebildet kann Zahnstein nicht durch Bürsten entfernt werden — erfordert professionelle Ultraschallentfernung unter Narkose."},
            {"term": "VOHC-Siegel",
             "simple_definition": "Gütezeichen des Veterinary Oral Health Council — vergeben an Zahnpflegeprodukte, die in klinischen Studien nachweislich Plaque oder Zahnstein um mindestens 20 % reduzieren."},
        ],
        "fr": [
            {"term": "Maladie parodontale",
             "simple_definition": "Infection et destruction des structures de soutien des dents — gencives, ligament parodontal et os alvéolaire. Commence par la plaque, évolue vers le tartre, puis l'inflammation des gencives et la perte osseuse."},
            {"term": "Tartre dentaire (calcul dentaire)",
             "simple_definition": "Plaque minéralisée sur la surface de la dent. Une fois formé, le tartre ne peut pas être éliminé par le brossage — nécessite un détartrage professionnel sous anesthésie."},
            {"term": "Label VOHC",
             "simple_definition": "Approbation du Veterinary Oral Health Council accordée aux produits dentaires ayant prouvé en essais cliniques une réduction de la plaque ou du tartre d'au moins 20 %."},
        ],
        "es": [
            {"term": "Enfermedad periodontal",
             "simple_definition": "Infección y destrucción de las estructuras de soporte dentario — encías, ligamento periodontal y hueso alveolar. Comienza con placa, avanza a sarro, luego inflamación de encías y pérdida ósea."},
            {"term": "Sarro dental (cálculo dental)",
             "simple_definition": "Placa mineralizada sobre la superficie del diente. Una vez formado no puede eliminarse con cepillado — requiere detartraje profesional con ultrasonidos bajo anestesia."},
            {"term": "Sello VOHC",
             "simple_definition": "Aprobación del Veterinary Oral Health Council otorgada a productos dentales que han demostrado en ensayos clínicos reducir la placa o el sarro en al menos un 20 %."},
        ],
        "tr": [
            {"term": "Periodontal hastalık",
             "simple_definition": "Dişleri destekleyen yapılarda enfeksiyon ve yıkım — diş eti, periodontal ligaman ve çene kemiği. Plakla başlar, diş taşına, ardından diş eti iltihabına ve kemik kaybına ilerler."},
            {"term": "Diş taşı (dental kalkülüs)",
             "simple_definition": "Diş yüzeyinde mineralleşmiş plak. Diş taşı oluştuktan sonra fırçalamayla çıkarılamaz — anestezi altında ultrasonik ekipmanla profesyonel temizlik gerektirir."},
            {"term": "VOHC sertifikası",
             "simple_definition": "Veteriner Ağız Sağlığı Konseyi onayı — klinik deneylerde plak veya diş taşını en az %20 azalttığı kanıtlanan dental ürünlere verilen sertifika."},
        ],
        "ar": [
            {"term": "مرض اللثة (أمراض دواعم السن)",
             "simple_definition": "عدوى وتدمير للهياكل الداعمة للأسنان — اللثة والرباط اللثوي وعظم الفك. يبدأ بالبلاك ويتطور إلى الحجر الجيري ثم التهاب اللثة وفقدان العظم."},
            {"term": "الحجر الجيري (طرطار الأسنان)",
             "simple_definition": "بلاك متكلس على سطح الأسنان. بمجرد تكوّنه لا يمكن إزالته بالفرشاة — يتطلب تنظيفاً احترافياً بجهاز الموجات فوق الصوتية تحت التخدير."},
            {"term": "ختم VOHC",
             "simple_definition": "اعتماد مجلس صحة الفم البيطري — يمنح للمنتجات السنية التي أثبتت في التجارب السريرية تقليل البلاك أو الحجر الجيري بنسبة 20% على الأقل."},
        ],
    },
}


async def seed():
    async with AsyncSessionLocal() as session:
        total = 0
        for lesson_id, locales in TRANSLATIONS.items():
            for locale, glossary in locales.items():
                await session.execute(
                    text("""
                        UPDATE lesson_translations
                        SET lay_glossary = :glossary
                        WHERE lesson_id = :lesson_id AND locale = :locale
                    """),
                    {"glossary": json.dumps(glossary, ensure_ascii=False), "lesson_id": lesson_id, "locale": locale}
                )
                total += 1
        await session.commit()
        print(f"Updated {total} lesson_translation rows with multilingual glossary terms.")


if __name__ == "__main__":
    asyncio.run(seed())
