import json
RFP="docs/ESCROW-ACCOUNTS/RFP_ESCROW_ACCOUNTS_26PROC020137847_ΨΣ8Σ469Η4Σ-ΝΛΘ.pdf"
ESPD="docs/ESCROW-ACCOUNTS/ΕΕΕΣ_ESCROW_ACCOUNTS_ψηφιακή υπογραφή.pdf"
EN="docs/ESCROW-ACCOUNTS/E-Notice Escrow Accounts_26PROC020137741.pdf"
def c(sec,pdf,doc=None,file="RFP",quote=None):
    d={"file":{"RFP":RFP,"ESPD":ESPD,"ENOTICE":EN}[file],"section":sec,"pdf_page":pdf}
    if doc: d["doc_page"]=doc
    if quote: d["quote"]=quote
    return d
R={
"notice":{
 "ted_publication_number":"769674-2026",
 "ted_url":"https://ted.europa.eu/en/notice/-/detail/769674-2026",
 "oj_reference":"2026/S 215-769674",
 "adam_diakiryxi":"26PROC020137847","ada":"ΨΣ8Σ469Η4Σ-ΝΛΘ","adam_enotice":"26PROC020137741",
 "esidis_system_no":"589064",
 "buyer":"ΚΟΙΝΩΝΙΑ ΤΗΣ ΠΛΗΡΟΦΟΡΙΑΣ Μ.Α.Ε. (ΚτΠ Μ.Α.Ε.), ΑΦΜ 999983307, Λεωφ. Συγγρού 194, 176 71 Καλλιθέα",
 "contact":"Σπύρου Θεοδώρα/Δώρα, 213 1300771 / 213 1300700, dspyrou@ktpae.gr / info@ktpae.gr",
 "title":"Παροχή Υπηρεσιών Συντήρησης, Υποστήριξης και Παραμετροποίησης του Πληροφοριακού Συστήματος Μηχανισμού Πληρωμών Προγραμμάτων Επιδοτήσεων (Escrow Accounts) της Κοινωνίας της Πληροφορίας Μ.Α.Ε.",
 "cpv":"72000000-5","procedure":"Ηλεκτρονικός Διεθνής Ανοικτός Άνω των Ορίων (άρθρο 27 ν.4412/2016)",
 "lots":"single lot (no division into lots)",
 "award_criterion":"Πλέον συμφέρουσα από οικονομική άποψη – βέλτιστη σχέση ποιότητας-τιμής; technical 80% / price 20%",
 "value":{"initial_ex_vat":200000.00,"initial_inc_vat":248000.00,"option_ex_vat":100000.00,"total_with_option_ex_vat":300000.00,"total_with_option_inc_vat":372000.00,
          "split_initial":{"support_maintenance_12m":125000.00,"parametrisation_packages":"5 x 15,000 = 75,000"},
          "cite":[c("Συνοπτικά στοιχεία Έργου",10,3),c("1.3",17,10),c("Παράρτημα V",104,97)]},
 "duration":"12 months","cite_duration":c("1.3",17,10),
 "dates":{"published_esidis":"2026-11-06","clarifications_deadline":"2026-11-18 (23:59:59 per e-Notice)",
          "submission_deadline":"2026-12-07 14:00 Europe/Athens (Monday)","opening_technical":"2026-12-11 14:00 (Friday, 4 working days after)",
          "cite":[c("Συνοπτικά στοιχεία Έργου",11,4),c("1.5",21),c("2.1.3",23,16),c("3.1.1",61,54),c("5.1.11",None,file="ENOTICE")]},
 "submission":"Electronic only via ΕΣΗΔΗΣ www.promitheus.gov.gr (system no. 589064); Greek language; advanced e-signature on qualified certificate required; ESPD PDF digitally signed; original paper participation guarantee (unless e-issued) delivered in sealed envelope to ΚτΠ before opening",
 "cite_submission":[c("1.1",15,8),c("2.4.2.1",52,45),c("2.4.2.5",54,47)],
 "docs_public_at":["https://www.ktpae.gr/wp-content/uploads/2026/11/ESCROW-ACCOUNTS.zip","https://cerpp.eprocurement.gov.gr/khmdhs-opendata/notice/attachment/26PROC020137847"],
 "page_offset_note":"RFP PDF has a 7-page decision preamble: body PDF page N = printed page N-7 (printed footer 'X - 103'). Annex II (ESPD) is appended as PDF pp.111-137 with no printed numbering."
},
"documents":[
 # group: agent_fill = agent can draft/fill fully; human_sign = agent drafts text, human signs/notarises; human_issue = third party / official portal issues; attach = existing company material to attach
 {"id":"espd","name":"European Single Procurement Document (ESPD)","greek":"Ευρωπαϊκό Ενιαίο Έγγραφο Σύμβασης (ΕΕΕΣ) – Παράρτημα ΙΙ","group":"agent_fill","then":"legal rep digitally signs (PDF)","envelope":"Δικαιολογητικά Συμμετοχής–Τεχνική Προσφορά",
  "notes":"Parts I (pre-filled by buyer), II A-D, III A-D, IV only section α (global yes), VI. Separate ESPD per JV member, per relied-on entity (II A-B, III, IV, VI) and per subcontractor >30% (II A-B, III, VI). Signature date must fall inside the submission window (06-11-2026..07-12-2026). XML template is on ΕΣΗΔΗΣ only (not in public ZIP).",
  "cite":[c("2.2.9.1",38,31),c("2.2.9.1",39,32),c("2.4.3.1 α",56,49),c("2.4.3.1 ΕΕΕΣ α-δ",57,50),c("Παράρτημα ΙΙ",100,93),c("Μέρος IV α",26,file="ESPD")]},
 {"id":"espd_cover_decl","name":"Accompanying solemn declaration clarifying ESPD (optional)","greek":"Συνοδευτική υπεύθυνη δήλωση ΕΕΕΣ","group":"agent_fill","then":"human signs","cite":[c("2.2.9.1",38,31),c("2.2.9.1",39,32),c("2.4.3.1 α",56,49)]},
 {"id":"participation_guarantee","name":"Participation guarantee letter","greek":"Εγγυητική επιστολή συμμετοχής (Παράρτημα VII.I)","group":"human_issue","issuer":"bank/insurer/ΤΜΕΔΕ/Ταμείο Παρακαταθηκών","amount_eur":4000.00,
  "rule":"2% of budget excl. VAT (=initial €200,000, NOT €300,000 with option); valid ≥30 days after offer validity; original paper copy before opening unless e-issued — otherwise offer rejected",
  "agent_role":"pre-fill the Annex VII.I template fields (amount, title, deadline, validity date) for the bank",
  "cite":[c("2.2.2.1",27,20,quote="ποσοστό 2% του προϋπολογισμού του Έργου (μη συμπεριλαμβανομένου ΦΠΑ), ήτοι ποσό τέσσερις χιλιάδες Ευρώ (4.000,00€)"),c("2.1.5",24,17),c("2.4.2.5",54,47),c("Παράρτημα VII.I",106,99)]},
 {"id":"russia_sanctions_decl","name":"Declaration on Russia sanctions (Reg. 833/2014 art. 5k)","greek":"Υπεύθυνη Δήλωση Κανονισμού (ΕΕ) 2022/576 – Παράρτημα VI","group":"agent_fill","then":"legal rep signs","envelope":"Δικαιολογητικά Συμμετοχής",
  "notes":"Annex VI body says 2022/578 while its heading and 2.2.1/2.4.3.1 say 2022/576 (source inconsistency).",
  "cite":[c("2.2.1 παρ.2",26,19),c("2.4.3.1 γ",56,49),c("Παράρτημα VI",105,98)]},
 {"id":"technical_offer","name":"Technical offer","greek":"Τεχνική Προσφορά (Παράρτημα IV)","group":"agent_fill","then":"digitally signed PDF, compressed, preferably one file",
  "structure":["1.1 Περιβάλλον της Σύμβασης","2.1 Υπηρεσίες συντήρησης & υποστήριξης","2.2 Υπηρεσίες παραμετροποίησης","3.1 Παραδοτέα–Χρονοδιάγραμμα","3.2 Ομάδα Έργου–Σχήμα Διοίκησης","3.3 Μεθοδολογία Διοίκησης & Διασφάλισης Ποιότητας","4 Πίνακες Οικονομικής Προσφοράς ΧΩΡΙΣ τιμές"],
  "notes":"Must state subcontracted share and subcontractors. Any price in the technical envelope = rejection. Scored K1 30% / K2 40% / K3 30%, 100–150 pts each; <100 = rejection.",
  "cite":[c("2.4.3.2",57,50),c("2.3.1",50,43),c("2.3.2.1",51,44),c("2.4.6 η",60,53),c("Παράρτημα IV",103,96)]},
 {"id":"financial_offer","name":"Financial offer table","greek":"Οικονομική Προσφορά (Παράρτημα V)","group":"agent_fill","then":"digitally signed PDF in separate envelope",
  "notes":"Lines: (1) support & maintenance 1 year — €125,000 cap; (2) parametrisation packages 5 × €15,000 = €75,000 cap. Price in EUR excl. VAT, fixed, ≤ budget; words prevail over figures; must state the payment method of §5.1.",
  "cite":[c("2.4.4",58,51),c("Παράρτημα V",104,97),c("5.1",79,72)]},
 {"id":"project_list","name":"List of main similar projects (last 5 years)","greek":"Κατάλογος κυριότερων συναφών έργων (Β.4 3.1)","group":"agent_fill","then":"backed by certificates/protocols of good execution from public clients (human_issue) or declarations for private clients",
  "cite":[c("2.2.9.2 Β.4",44,37)]},
 {"id":"team_tables","name":"Project team tables (own staff / subcontractors / external) with person-months and %","greek":"Πίνακες Ομάδας Έργου (Β.4 4.1)","group":"agent_fill","cite":[c("2.2.9.2 Β.4",45,38)]},
 {"id":"cvs","name":"CVs of project team","greek":"Βιογραφικά σημειώματα (Παράρτημα ΙΙΙ)","group":"agent_fill","then":"each person confirms",
  "notes":"Template header on PDF pp.102-103 carries the title of a DIFFERENT KtP project («Παροχή υπηρεσιών φιλοξενίας, υποστήριξης και επέκτασης υφιστάμενων πληροφοριακών συστημάτων...») — do not copy it.",
  "cite":[c("2.2.9.2 Β.4 4.2",46,39),c("Παράρτημα ΙΙΙ",101,94)]},
 {"id":"cooperation_decls","name":"Cooperation declarations of external collaborators and subcontractors","greek":"Υπεύθυνες δηλώσεις συνεργασίας εξωτερικών συνεργατών/υπεργολάβων","group":"human_sign","cite":[c("2.2.9.2 Β.4",46,39),c("2.2.9.2 Β.10",48,41)]},
 {"id":"criminal_record","name":"Criminal record extract (company reps / board members)","greek":"Απόσπασμα ποινικού μητρώου","group":"human_issue","validity":"issued ≤3 months before submission","phase":"provisional contractor (3.2)","cite":[c("2.2.9.2 Β.1 α",41,34)]},
 {"id":"tax_clearance","name":"Tax clearance certificate","greek":"Αποδεικτικό φορολογικής ενημερότητας (ΑΑΔΕ)","group":"human_issue","validity":"valid at submission, else ≤3 months","phase":"provisional contractor","cite":[c("2.2.9.2 Β.1 β i",41,34)]},
 {"id":"insurance_clearance","name":"Social-security clearance certificate","greek":"Ασφαλιστική ενημερότητα (e-ΕΦΚΑ)","group":"human_issue","validity":"valid at submission, else ≤3 months","phase":"provisional contractor","cite":[c("2.2.9.2 Β.1 β ii",41,34)]},
 {"id":"insurance_orgs_decl","name":"Declaration listing social-security bodies the company pays","greek":"Υπεύθυνη δήλωση φορέων κύριας & επικουρικής ασφάλισης","group":"human_sign","cite":[c("2.2.9.2 Β.1 β ii",41,34)]},
 {"id":"no_final_judgment_decl","name":"Declaration: no final judgment for unpaid taxes/contributions","greek":"Υπεύθυνη δήλωση μη έκδοσης τελεσίδικης απόφασης για φόρους/εισφορές","group":"human_sign","cite":[c("2.2.9.2 Β.1 β iii",41,34)]},
 {"id":"solvency_cert","name":"Single certificate of judicial solvency","greek":"Ενιαίο Πιστοποιητικό Δικαστικής Φερεγγυότητας (Πρωτοδικείο)","group":"human_issue","validity":"≤3 months","cite":[c("2.2.9.2 Β.1 γ i",42,35)]},
 {"id":"gemi_not_dissolved","name":"GEMI certificate: not dissolved/in liquidation (+ extra certs for ΙΚΕ/ΕΠΕ)","greek":"Πιστοποιητικό ΓΕΜΗ περί μη λύσης/εκκαθάρισης","group":"human_issue","validity":"≤3 months","cite":[c("2.2.9.2 Β.1 γ ii",42,35)]},
 {"id":"taxisnet_card","name":"Taxisnet 'Στοιχεία Μητρώου/Επιχείρησης' printout (activity not suspended)","greek":"Εκτύπωση καρτέλας Στοιχεία Μητρώου/Επιχείρησης (taxisnet)","group":"human_issue","cite":[c("2.2.9.2 Β.1 γ iii",42,35)]},
 {"id":"other_exclusion_decl","name":"Declaration: other 2.2.3.3 exclusion grounds do not apply","greek":"Υπεύθυνη δήλωση μη συνδρομής λόγων 2.2.3.3","group":"human_sign","cite":[c("2.2.9.2 Β.1 δ",42,35)]},
 {"id":"horizontal_exclusion_decl","name":"Declaration: no horizontal exclusion sanction","greek":"Υπεύθυνη δήλωση μη επιβολής οριζόντιου αποκλεισμού","group":"human_sign","cite":[c("2.2.9.2 Β.1 ε",42,35)]},
 {"id":"integrity_decl","name":"Declaration per Annex IX (integrity clause)","greek":"Υπεύθυνη Δήλωση σύμφωνα με Παράρτημα ΙΧ – Ρήτρα Ακεραιότητας","group":"human_sign","cite":[c("2.2.9.2 Β.1 στ",42,35),c("Παράρτημα IX",109,102)]},
 {"id":"bribery_affidavit","name":"Sworn affidavit of legal rep: entity not convicted of bribery (art. 73 §1, ν.5090/2024)","greek":"Ένορκη βεβαίωση νομίμου εκπροσώπου","group":"human_sign","notes":"sworn before notary/court; ≤3 months old (Β.11)","cite":[c("2.2.9.2 Β.1 ζ",42,35),c("Β.11",49,42)]},
 {"id":"gemi_registration","name":"Professional register / GEMI registration certificate","greek":"Πιστοποιητικό εγγραφής ΓΕΜΗ / επαγγελματικού μητρώου","group":"human_issue","validity":"≤30 WORKING days before submission","cite":[c("2.2.9.2 Β.2",43,36)]},
 {"id":"financials","name":"Published financial statements 2023-2025 (or draft 2025 balance sheet + P&L + e-signed declaration of turnover; or tax returns/E3 if no balance sheet)","greek":"Δημοσιευμένες χρηματοοικονομικές καταστάσεις 2023-2025","group":"attach","cite":[c("2.2.9.2 Β.3",43,36),c("2.2.9.2 Β.3",44,37)]},
 {"id":"good_execution_certs","name":"Certificates / acceptance protocols / good-execution statements for each listed project","greek":"Βεβαιώσεις καλής εκτέλεσης / πρωτόκολλα παραλαβής","group":"human_issue","cite":[c("2.2.9.2 Β.4 3.1",44,37)]},
 {"id":"iso_certs","name":"ISO certificates (9001, 20000-1, 27001, 27701, 22301, 37001)","greek":"Πιστοποιητικά ISO","group":"attach","cite":[c("2.2.7",36,29),c("2.2.9.2 Β.5",46,39)]},
 {"id":"representation","name":"GEMI certificate of current representation (≤30 working days) + general certificate of changes (≤3 months); board minutes if extra signatory","greek":"Πιστοποιητικό ισχύουσας εκπροσώπησης / γενικό πιστοποιητικό μεταβολών ΓΕΜΗ","group":"human_issue","cite":[c("2.2.9.2 Β.6",46,39),c("2.2.9.2 Β.6 ii",47,40)]},
 {"id":"jv_agreement","name":"JV agreement (only if bidding as a union)","greek":"Συμφωνητικό ένωσης","group":"agent_fill","then":"all members sign","cite":[c("2.2.9.2 Β.8",48,41)]},
 {"id":"capacity_commitment","name":"Third-party capacity commitment (only if relying on others)","greek":"Δέσμευση τρίτου φορέα (στήριξη στην ικανότητα)","group":"agent_fill","then":"third party signs","cite":[c("2.2.9.2 Β.9",48,41)]},
 {"id":"performance_guarantee","name":"Performance guarantee (at contract signature)","greek":"Εγγυητική επιστολή καλής εκτέλεσης (Παράρτημα VII.II)","group":"human_issue","amount_eur":8000.00,"rule":"4% of estimated value excl. VAT and excl. options","cite":[c("4.1",72,65),c("Παράρτημα VII.II",107,100)]}
],
"exclusion_criteria":{
 "section":"2.2.3 (PDF pp.28-32 / printed 21-25)","cite":[c("2.2.3",28,21)],
 "espd_part_III_grounds":["Συμμετοχή σε εγκληματική οργάνωση","Διαφθορά","Απάτη","Τρομοκρατικά εγκλήματα","Νομιμοποίηση εσόδων / χρηματοδότηση τρομοκρατίας","Παιδική εργασία / εμπορία ανθρώπων","Καταβολή φόρων","Καταβολή εισφορών κοινωνικής ασφάλισης","Αθέτηση υποχρεώσεων περιβαλλοντικού/κοινωνικού/εργατικού δικαίου","Πτώχευση / εξυγίανση / πτωχευτικός συμβιβασμός / αναγκαστική διαχείριση / αναστολή δραστηριοτήτων","Σοβαρό επαγγελματικό παράπτωμα","Συμφωνίες στρέβλωσης ανταγωνισμού","Σύγκρουση συμφερόντων / εμπλοκή στην προετοιμασία","Πρόωρη καταγγελία προηγούμενης σύμβασης","Ψευδείς δηλώσεις"],
 "espd_part_III_D":"no national grounds selected",
 "russia":"Reg. (EU) 833/2014 art. 5k as amended by 2022/576 (2.2.1 §2)",
 "horizontal_exclusion":"2.2.3.7",
 "self_cleaning":"2.2.3.5"
},
"selection_criteria":[
 {"id":"suitability","rule":"Professional activity related to IT services; registered in GEMI/professional register","cite":[c("2.2.4",32,25)]},
 {"id":"turnover","rule":"TOTAL (cumulative, not annual average) turnover for 2023+2024+2025 ≥ 200% of budget excl. VAT and excl. option","computed_threshold_eur":400000.00,"computed_from":"200% × €200,000","cite":[c("2.2.5 §1",33,26,quote="Ο συνολικός κύκλος εργασιών των τριών τελευταίων διαχειριστικών χρήσεων (2023, 2024, 2025) ... τουλάχιστον ίσου με το διακόσια τοις εκατό (200%) του προϋπολογισμού του υπό ανάθεση έργου (μη συμπεριλαμβανομένου Φ.Π.Α. και δικαιώματος προαίρεσης)")]},
 {"id":"profitability","rule":"Profitable in each of the last 3 financial years","cite":[c("2.2.5 §2",33,26)]},
 {"id":"experience_escrow","rule":"Within 2021–2026 (to deadline) completed ≥5 projects for public-sector bodies implementing escrow-account payment systems, each with: citizen ID via ΓΓΠΣΨΔ interoperability; payment request processing; interoperability with credit institutions (at least all Greek banks under the ECB SSM); MIS/reporting; financial transaction documents","cite":[c("2.2.6.1 I",33,26),c("2.2.6.1 I",34,27)]},
 {"id":"experience_sla","rule":"≥1 of those projects included production operation + SLA-based support (KPIs, SLA reports, incident handling, parametrisation) with budget ≥100% of this project's budget excl. VAT","computed_threshold_eur":200000.00,"cite":[c("2.2.6.1 I",34,27)]},
 {"id":"experience_transformation","rule":"≥1 consulting & technology project for digital transformation of processes incl. maintenance-support, for public/wider public sector","cite":[c("2.2.6.1 II",34,27)]},
 {"id":"team","rule":"Minimum team (on pain of exclusion): 1 Project Manager (degree + master's in IT/economics/CompEng, 12y public-sector ICT consulting, PM in ≥3 projects in last 5y incl. Greek public payment system); 2 Senior Developers (IT/CompEng degree, ≥5y); 2 Developers (≥3y); 1 InfoSec officer (degree + master's, ISO 27001 auditor, ≥20y general of which ≥10y infosec, ≥2 valid certs from CCLP/CISA/Certified Phishing Specialist/Certified Insider Thread Specialist/Certified Security Awareness Specialist/CISM); 1 DPO (law degree, master's in law/economics/finance, ≥10y of which 5y GDPR, GDPR/DPO cert). Experience counts only after the base degree.","cite":[c("2.2.6.2",34,27),c("2.2.6.2",35,28)]},
 {"id":"iso","rule":"Valid certificates from ΕΣΥΔ/internationally accredited body, scope covering IS analysis/design/development/installation/support: ISO 9001:2015, ISO/IEC 20000-1:2018, 'ISO 27001:2019' (sic), 'ISO 27701:2019', ISO 22301:2019, ISO 37001:2016. In a JV EVERY member must hold them. Certificates 'issued … up to 30 days before the deadline'.","cite":[c("2.2.7",36,29),c("2.2.7",37,30)]},
 {"id":"espd_part_iv","rule":"In ESPD Part IV fill ONLY section α (global indication) — do not fill A–D","cite":[c("2.2.9.1",38,31),c("2.2.9.1",39,32),c("Παράρτημα ΙΙ",100,93)]}
],
"evaluation":{"technical":{"K1 Αντίληψη & κατανόηση":"30%","K2 Ομάδα Έργου":"40%","K3 Μεθοδολογία & Ποιότητα":"30%","scale":"100–150 per criterion; <100 → rejection"},"formula":"A = 0.80·(T/Tmax) + 0.20·(Omin/O)","cite":[c("2.3.1",50,43),c("2.3.2",51,44)]},
"traps":[
 {"id":"budget_base","text":"Three different 'budgets': €200k initial (basis for turnover 200%, participation guarantee 2%, performance guarantee 4%, SLA-project ≥100%), €300k with 50% option (what TED's procedure-level 'estimated value' shows), €248k/€372k incl. VAT.","cite":[c("1.3",17,10),c("2.2.2.1",27,20),c("2.2.5",33,26),c("4.1",72,65)]},
 {"id":"turnover_total_vs_annual","text":"Turnover test is the SUM of 3 years (≥€400k total), not an annual or average figure (contrast: backup tender uses 'μέσο ετήσιο').","cite":[c("2.2.5",33,26)]},
 {"id":"validity_windows","text":"Different freshness rules: criminal record / solvency / GEMI dissolution / changes cert ≤3 months; GEMI registration & representation ≤30 WORKING days; affidavits ≤3 months; solemn declarations must be dated AFTER the invitation to submit supporting docs; ESPD signature date inside submission window.","cite":[c("Β.1",41,34),c("Β.2",43,36),c("Β.6",46,39),c("Β.11",49,42),c("2.2.9.1",38,31),c("2.2.9.1",39,32)]},
 {"id":"offer_and_guarantee_validity","text":"Offer valid 12 months from the day after the deadline; participation guarantee must be valid ≥30 days beyond that (derived: offer valid to ~07-12-2027 → guarantee to ≥ ~06-01-2028; verify).","cite":[c("2.4.5",58,51),c("2.2.2.1",27,20)]},
 {"id":"paper_original","text":"Even though submission is electronic, the ORIGINAL participation guarantee (unless e-issued) must physically reach ΚτΠ (Συγγρού 194) in a sealed envelope before opening (11-12-2026 14:00) or the offer is rejected; if posted, upload the courier receipt via ΕΣΗΔΗΣ 'Επικοινωνία'.","cite":[c("2.2.2.1",27,20),c("2.4.2.5",55,48)]},
 {"id":"no_prices_in_technical","text":"Technical offer must include the financial tables WITHOUT prices; any price there = rejection; also differences between priced and unpriced tables = rejection.","cite":[c("Παράρτημα IV",103,96),c("2.4.6 η, ιε",60,53)]},
 {"id":"signatures","text":"Advanced e-signature on a qualified certificate; ESPD, technical, financial PDFs digitally signed; ΕΣΗΔΗΣ-generated PDF summaries must also be signed and attached to each sub-envelope.","cite":[c("2.4.2.1",52,45),c("2.4.2.4",53,46)]},
 {"id":"source_errors","text":"Errors IN THE SOURCE the agent must not 'fix' silently: (a) ISO 27001:2019 / ISO 27701:2019 (editions do not match the real standards); (b) Annex VI cites Reg. 2022/578 vs 2022/576 elsewhere; (c) 2.2.7 ends with 'οφείλουν να διαθέτουν επιπλέων των ανωτέρω και:' followed by nothing; (d) score formula 'B = σ1χΚ1 + σ2χΚ2 + σ3χΚ3 + σ4χ4' with only 3 criteria; (e) Annex III/IV page headers name a different KtP project; (f) 2.1.6 sends data-protection info to 'παράρτημα IX' but it is Annex VIII; (g) stray 'http://www.eaadhsy.gr/http://www.hsppa.gr/.' in 2.2.9.1; (h) fax 213 1300801 (RFP) vs 2131300800-1 (ESPD); (i) 2.4.4 says pick 'one of the payment methods of 5.1' but 5.1 defines one per service block.","cite":[c("2.2.7",36,29),c("Παράρτημα VI",105,98),c("2.3.2.1",51,44),c("Παράρτημα ΙΙΙ/IV headers",102,95),c("2.1.6",25,18),c("2.2.9.1",38,31),c("2.2.9.1",39,32),c("2.4.4",58,51)]},
 {"id":"wired_criteria","text":"Selection is very narrow (5 public escrow-payment projects, 20-year infosec expert, six ISOs held by every JV member) — a typical SME will NOT qualify; the honest output for most profiles is 'not eligible, here is why (clause)' or 'needs a JV/capacity lending'.","cite":[c("2.2.6.1",33,26),c("2.2.6.2",35,28),c("2.2.7",37,30)]}
],
"not_obtained":["ESPD .xml template (only on ΕΣΗΔΗΣ system 589064, JS-only page; not in public ZIP)","Any clarifications/amendments published after 06-11-2026 on ΕΣΗΔΗΣ"]
}
json.dump(R,open("requirements.json","w"),ensure_ascii=False,indent=2)
print("ok",len(R["documents"]))
