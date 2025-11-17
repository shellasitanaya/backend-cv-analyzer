from typing import Dict, List, Tuple
import re
from app.services.cv_parser import extract_text
from app.services.ai_analyzer import parse_candidate_info

class AstraScoringService:
    """Service khusus untuk scoring lowongan Astra dengan jurusan yang lebih luas"""
    
    # Requirements untuk masing-masing lowongan - Enhanced dengan jurusan data science/analytics
    JOB_REQUIREMENTS = {
        "erp_business_analyst": {
            "wajib": {
                "jurusan": [
                    # Jurusan teknik informatika dan komputer
                    "teknik informatika", "informatika", "ilmu komputer", "computer science", 
                    "sistem informasi", "information systems", "teknik komputer", "computer engineering",
                    "teknologi informasi", "information technology", "software engineering", 
                    "rekayasa perangkat lunak",
                    # Jurusan sib
                    "business information system", "business information systems",
                    "sistem informasi bisnis", "information system business",
                    # Jurusan data science dan analytics
                    "data science", "ilmu data", "data analytics", "analisis data", 
                    "business intelligence", "data mining", "penambangan data", "big data",
                    "artificial intelligence", "kecerdasan buatan", "machine learning", 
                    "pembelajaran mesin", "statistika", "statistics", "matematika", "mathematics",
                    # Jurusan bisnis dan management  
                    "teknik industri", "industrial engineering", "bisnis", "business",
                    "manajemen", "management", "manajemen informatika", "management information systems",
                    "sistem informasi manajemen", "management information systems"
                    
                ],
                "strata": ["s1", "bachelor", "sarjana"],
                "min_ipk": 3.00
            },
            "job_requirements": [
                # Bilingual keyword groups
                "analytical skill analitis kemampuan analisis business process identifikasi proses bisnis",
                "proses modelling modeling tools alat bpmn uml flowchart dfd user stories",
                "data modelling modeling sql nosql star schema normalisasi normalization",
                "app application development architecture arsitektur pengembangan mvc spa",
                "software development life cycle sdlc siklus hidup pengembangan perangkat lunak",
                "power bi modelling modeling report design desain laporan dashboard"
            ],
            "nice_to_have": [
                "erp", "enterprise resource planning", "healthcare", "hospital", "rumah sakit", 
                "blueprint", "business process", "proses bisnis", "analytical thinking", 
                "system analysis", "analisis sistem", "healthcare systems", "sistem kesehatan",
                "hospital management", "manajemen rumah sakit", "medical systems", "sistem medis"
            ]
        },
        "it_data_engineer": {
            "wajib": {
                "jurusan": [
                    # Jurusan komputer dan IT
                    "ilmu komputer", "computer science", "teknologi informasi", "information technology",
                    "teknik informatika", "informatics engineering", "sistem informasi", "information systems",
                    # Jurusan data science dan engineering  
                    "data science", "ilmu data", "data engineering", "rekayasa data", "data analytics",
                    "analisis data", "big data", "data besar", "data mining", "penambangan data",
                    "business intelligence", "kecerdasan bisnis", "artificial intelligence", "kecerdasan buatan",
                    "machine learning", "pembelajaran mesin", "statistika", "statistics", 
                    "matematika", "mathematics", "fisika", "physics",
                    # Jurusan teknik lainnya
                    "teknik elektro", "electrical engineering", "teknik telekomunikasi", "telecommunications"
                ],
                "strata": ["s1", "bachelor", "sarjana"],
                "min_ipk": 3.00,
                "min_pengalaman": 3
            },
            "job_requirements": [
                "pengalaman teknis technical experience merancang design model data data model",
                "mahir proficient kueri query sql sql server database",
                "alat big data hadoop spark kafka data processing",
                "alat etl extract transform load informatica talend pentaho data integration"
            ],
            "nice_to_have": [
                "data management", "manajemen data", "data pipeline", "pipelines data", 
                "data warehouse", "gudang data", "cloud", "aws", "azure", "google cloud",
                "data governance", "tata kelola data", "data quality", "kualitas data", 
                "data integration", "integrasi data", "data modeling", "pemodelan data",
                "business intelligence", "kecerdasan bisnis", "data analytics", "analitik data"
            ]
        }
    }

    @staticmethod
    def analyze_cv_for_job(cv_text: str, job_type: str) -> Dict:
        """
        Analisis CV untuk lowongan spesifik Astra dengan jurusan yang lebih luas
        """
        print(f"🔍 [ASTRA SCORING] Memulai analisis untuk: {job_type}")
        
        if job_type not in AstraScoringService.JOB_REQUIREMENTS:
            raise ValueError(f"Job type {job_type} tidak dikenali")
        
        requirements = AstraScoringService.JOB_REQUIREMENTS[job_type]
        
        try:
            parsed_info = parse_candidate_info(cv_text)
            parsed_info['cv_full_text'] = cv_text

            parsed_info['gpa'] = float(parsed_info.get('gpa') or 0.0)
            parsed_info['experience'] = int(parsed_info.get('experience') or 0)

            print(f"✅ [ASTRA SCORING] Parsing berhasil - Language: {parsed_info.get('language', 'unknown')}")
            print(f"✅ [ASTRA SCORING] Major detected: {parsed_info.get('major', 'Not found')}")

            if parsed_info.get('gpa') is None:
                parsed_info['gpa'] = 0.0
                print("⚠️ [ASTRA SCORING] GPA is None, set to 0.0")
            
            if parsed_info.get('experience') is None:
                parsed_info['experience'] = 0
                print("⚠️ [ASTRA SCORING] Experience is None, set to 0")
            
            # ✅ CONVERT TO PROPER TYPES
            try:
                parsed_info['gpa'] = float(parsed_info['gpa'])
            except (ValueError, TypeError):
                parsed_info['gpa'] = 0.0
                print("⚠️ [ASTRA SCORING] Cannot convert GPA to float, using 0.0")
            
            try:
                parsed_info['experience'] = int(parsed_info['experience'])
            except (ValueError, TypeError):
                parsed_info['experience'] = 0
                print("⚠️ [ASTRA SCORING] Cannot convert experience to int, using 0")
            
            print(f"📊 [ASTRA SCORING] Sanitized - GPA: {parsed_info['gpa']}, Experience: {parsed_info['experience']}")
        except Exception as e:
            print(f"❌ [ASTRA SCORING] Parsing gagal: {e}")
            return {
                "lulus": False,
                "alasan": ["Gagal memproses CV - format tidak didukung"],
                "skor_akhir": 0,
                "detail_skor": {}
            }
        
        # 1. Check requirements wajib dengan matching jurusan yang lebih fleksibel
        wajib_result = AstraScoringService._check_wajib_requirements(parsed_info, requirements["wajib"], cv_text)
        
        if not wajib_result["lulus"]:
            print(f"❌ [ASTRA SCORING] Gagal requirements wajib: {wajib_result['alasan']}")
            return {
                "lulus": False,
                "alasan": wajib_result["alasan"],
                "skor_akhir": 0,
                "detail_skor": {
                    "wajib": wajib_result,
                    "job_requirements": {"skor": 0, "max_skor": 0, "persentase": 0},
                    "nice_to_have": {"skor": 0, "max_skor": 0, "persentase": 0}
                }
            }
        
        # 2. Hitung scoring job requirements dan nice to have
        job_req_score = AstraScoringService._calculate_job_requirements_score(cv_text, requirements["job_requirements"])
        nice_to_have_score = AstraScoringService._calculate_nice_to_have_score(cv_text, requirements["nice_to_have"])
        
        print(f"📊 [ASTRA SCORING] Job Req Score: {job_req_score}/{len(requirements['job_requirements'])}")
        print(f"📊 [ASTRA SCORING] Nice to Have Score: {nice_to_have_score}/{len(requirements['nice_to_have'])}")
        
        # 3. Hitung skor akhir (80% job requirements + 20% nice to have)
        job_req_percentage = (job_req_score / len(requirements["job_requirements"])) * 100 if requirements["job_requirements"] else 0
        nice_to_have_percentage = (nice_to_have_score / len(requirements["nice_to_have"])) * 100 if requirements["nice_to_have"] else 0
        skor_akhir = (job_req_percentage * 0.8) + (nice_to_have_percentage * 0.2)
        
        print(f"🎯 [ASTRA SCORING] Skor Akhir: {skor_akhir:.2f}%")
        
        return {
            "lulus": True,
            "skor_akhir": round(skor_akhir, 2),
            "detail_skor": {
                "wajib": wajib_result,
                "job_requirements": {
                    "skor": job_req_score,
                    "max_skor": len(requirements["job_requirements"]),
                    "persentase": round(job_req_percentage, 2)
                },
                "nice_to_have": {
                    "skor": nice_to_have_score,
                    "max_skor": len(requirements["nice_to_have"]),
                    "persentase": round(nice_to_have_percentage, 2)
                }
            },
            "parsed_info": parsed_info
        }

    @staticmethod
    @staticmethod
    def _check_wajib_requirements(parsed_info: Dict, wajib: Dict, cv_full_text: str = "") -> Dict:
        """
        Check requirements wajib dengan jurusan yang lebih fleksibel
        """
        alasan = []
        details = {}
        
        # ✅ FIX: Get cv_full_text from parameter or parsed_info
        if not cv_full_text:
            cv_full_text = parsed_info.get("cv_full_text", "")
        
        cv_full_text_lower = cv_full_text.lower()

        # Check jurusan dengan fuzzy matching yang lebih baik
        pendidikan = parsed_info.get("education", "").lower() if parsed_info.get("education") else ""
        jurusan_text = parsed_info.get("structured_profile_json", {}).get("education", "").lower()
        major_detected = parsed_info.get("major", "").lower()
        
        # ✅ Combine all text for matching
        all_education_text = f"{pendidikan} {jurusan_text} {major_detected} {cv_full_text_lower}".lower()
        
        print(f"🔍 [JURUSAN CHECK] Education text length: {len(all_education_text)} chars")
        print(f"🔍 [JURUSAN CHECK] Text sample: {all_education_text[:500]}...")
        
        # Fuzzy matching untuk jurusan
        jurusan_ok = False
        best_match_score = 0
        best_match_name = None
        
        for jurusan in wajib["jurusan"]:
            # ✅ METHOD 1: Exact phrase match (best)
            if jurusan in all_education_text:
                jurusan_ok = True
                details["jurusan_matched"] = jurusan
                details["match_method"] = "exact"
                print(f"  ✅ EXACT MATCH: '{jurusan}'")
                break
            
            # ✅ METHOD 2: Fuzzy word matching
            jurusan_words = [w for w in jurusan.split() if len(w) > 2]  # Skip short words
            if not jurusan_words:  # If all words too short, use original
                jurusan_words = jurusan.split()
            
            match_count = sum(1 for word in jurusan_words if word in all_education_text)
            match_score = match_count / len(jurusan_words) if jurusan_words else 0
            
            # Track best match
            if match_score > best_match_score:
                best_match_score = match_score
                best_match_name = jurusan
            
            # ✅ LOWER THRESHOLD: 40% match
            if match_score >= 0.4:
                jurusan_ok = True
                details["jurusan_matched"] = jurusan
                details["match_method"] = "fuzzy"
                details["match_score"] = match_score
                print(f"  ✅ FUZZY MATCH: '{jurusan}' ({match_count}/{len(jurusan_words)} words = {match_score:.2%})")
                break
        
        details["jurusan"] = jurusan_ok
        details["best_match"] = best_match_name
        details["best_match_score"] = best_match_score
        
        if not jurusan_ok:
            alasan.append(
                f"Jurusan tidak sesuai. Dibutuhkan jurusan terkait komputer, IT, data science, atau bisnis. "
                f"(Best match: {best_match_name} - {best_match_score:.1%})"
            )
            print(f"  ❌ NO MATCH. Best was '{best_match_name}' at {best_match_score:.2%}")
        
        # Check strata
        strata_ok = any(strata in all_education_text for strata in wajib["strata"])
        details["strata"] = strata_ok
        if not strata_ok:
            alasan.append(f"Strata pendidikan harus {wajib['strata'][0].upper()} atau setara")
        
        # Check IPK
        ipk = parsed_info.get("gpa", 0.0)
        if ipk is None:
            ipk = 0.0
        try:
            ipk = float(ipk)
        except (ValueError, TypeError):
            ipk = 0.0
        
        ipk_ok = ipk >= wajib["min_ipk"]
        details["ipk"] = ipk_ok
        details["ipk_value"] = ipk
        
        if not ipk_ok:
            alasan.append(f"IPK minimal {wajib['min_ipk']} (IPK saat ini: {ipk})")
        
        # Check pengalaman
        if "min_pengalaman" in wajib:
            pengalaman = parsed_info.get("experience", 0)
            if pengalaman is None:
                pengalaman = 0
            try:
                pengalaman = int(pengalaman)
            except (ValueError, TypeError):
                pengalaman = 0
            
            pengalaman_ok = pengalaman >= wajib["min_pengalaman"]
            details["pengalaman"] = pengalaman_ok
            details["pengalaman_value"] = pengalaman

            if not pengalaman_ok:
                alasan.append(f"Pengalaman minimal {wajib['min_pengalaman']} tahun (pengalaman saat ini: {pengalaman})")
        
        return {
            "lulus": len(alasan) == 0,
            "alasan": alasan if alasan else ["Semua requirements wajib terpenuhi"],
            "detail": details
        }


    @staticmethod
    def _calculate_job_requirements_score(cv_text: str, requirements: List[str]) -> float:
        """
        Hitung skor job requirements dengan enhanced bilingual matching
        """
        cv_text_lower = cv_text.lower()
        score = 0
        
        print(f"🔍 [JOB REQ SCORING] Analyzing {len(requirements)} requirements")
        
        for i, requirement in enumerate(requirements):
            # Setiap requirement adalah group keywords bilingual (OR condition dalam group)
            keyword_groups = requirement.split()
            matched_groups = 0
            
            for keyword_group in keyword_groups:
                # Dalam setiap group, cari apakah ada keyword yang match
                group_keywords = keyword_group.split()
                group_match = any(keyword in cv_text_lower for keyword in group_keywords)
                
                if group_match:
                    matched_groups += 1
            
            # Jika lebih dari 50% groups match, consider requirement terpenuhi
            requirement_fulfilled = matched_groups >= len(keyword_groups) * 0.5
            
            if requirement_fulfilled:
                score += 1
                print(f"  ✅ Requirement {i+1}: FULFILLED ({matched_groups}/{len(keyword_groups)} groups)")
            else:
                print(f"  ❌ Requirement {i+1}: NOT FULFILLED ({matched_groups}/{len(keyword_groups)} groups)")
        
        print(f"📊 [JOB REQ SCORING] Final Score: {score}/{len(requirements)}")
        return score

    @staticmethod
    def _calculate_nice_to_have_score(cv_text: str, nice_to_have: List[str]) -> float:
        """
        Hitung skor nice to have dengan bilingual matching
        """
        cv_text_lower = cv_text.lower()
        score = 0
        
        print(f"🔍 [NICE TO HAVE SCORING] Analyzing {len(nice_to_have)} items")
        
        for item in nice_to_have:
            # Untuk nice to have, exact match atau partial match diterima
            if item in cv_text_lower:
                score += 1
                print(f"  ✅ Nice to Have: '{item}' - FOUND")
            else:
                # Cek partial match untuk kata individual
                item_words = item.split()
                if len(item_words) > 1 and any(word in cv_text_lower for word in item_words):
                    score += 0.5  # Partial credit untuk partial match
                    print(f"  ⚠️ Nice to Have: '{item}' - PARTIAL MATCH")
                else:
                    print(f"  ❌ Nice to Have: '{item}' - NOT FOUND")
        
        print(f"📊 [NICE TO HAVE SCORING] Final Score: {score}/{len(nice_to_have)}")
        return score

    @staticmethod
    def get_job_descriptions() -> Dict:
        """Get deskripsi lengkap untuk masing-masing lowongan - Bilingual"""
        return {
            "erp_business_analyst": {
                "nama": "ERP Business Analyst Project - GSI",
                "deskripsi": "Menilai dan menganalisa ERP existing pada lingkup Rumah Sakit, memberikan rekomendasi perbaikan, menyusun blueprint, dan membantu implementasi ERP / Assess and analyze existing ERP systems in Hospital scope, provide improvement recommendations, develop blueprints, and assist in ERP implementation",
                "requirements_wajib": "S1 Teknik Informatika/Management Informatika/Sistem Informasi/Teknik Industri/Bisnis atau setara, IPK min 3.00 / Bachelor's degree in Computer Science/Information Systems/Industrial Engineering/Business or equivalent, minimum GPA 3.00",
                "job_requirements": [
                    "Strong analytical skill dalam identifikasi proses bisnis / Strong analytical skills in business process identification",
                    "Strong knowledge dalam proses modelling dan tools (BPMN, UML, Flowchart, DFD, User stories) / Strong knowledge in process modeling and tools",
                    "Strong knowledge dalam data modelling SQL dan NoSQL (konsep star schema dan normalisasi) / Strong knowledge in SQL and NoSQL data modeling (star schema and normalization concepts)",
                    "Strong understanding dalam app development architecture (MVC, SPA) / Strong understanding of application development architecture",
                    "Memiliki pengetahuan mengenai Software Development Life Cycle (SDLC) / Knowledge of Software Development Life Cycle",
                    "Memiliki pengetahuan Power BI modelling dan report design / Knowledge of Power BI modeling and report design"
                ],
                "preferred_skills": [
                    "ERP systems knowledge",
                    "Healthcare/Hospital domain experience", 
                    "Business process analysis",
                    "System blueprint development",
                    "Requirements gathering and documentation"
                ]
            },
            "it_data_engineer": {
                "nama": "IT Data Engineer - TAF", 
                "deskripsi": "Merancang dan mengimplementasikan sistem manajemen data yang andal untuk mendukung operasional perusahaan yang optimal / Design and implement reliable data management systems to support optimal company operations",
                "requirements_wajib": "S1 Ilmu Komputer/Teknologi Informasi/Teknik Informatika/Sistem Informasi atau setara, IPK min 3.00, Pengalaman min 3 tahun / Bachelor's degree in Computer Science/Information Technology/Informatics/Information Systems or equivalent, minimum GPA 3.00, minimum 3 years experience",
                "job_requirements": [
                    "Memiliki pengalaman teknis dalam merancang model data / Have technical experience in designing data models",
                    "Mahir dalam menulis kueri SQL dan terbiasa menggunakan SQL Server / Proficient in writing SQL queries and familiar with SQL Server", 
                    "Memahami alat Big Data seperti Hadoop, Spark, Kafka / Understand Big Data tools like Hadoop, Spark, Kafka",
                    "Memiliki pengetahuan yang baik mengenai alat ETL seperti Informatica, Talend, Pentaho / Have good knowledge of ETL tools like Informatica, Talend, Pentaho"
                ],
                "preferred_skills": [
                    "Data pipeline development",
                    "Cloud platform experience (AWS, Azure, GCP)",
                    "Data warehouse design", 
                    "Data governance and quality",
                    "Business intelligence tools"
                ]
            }
        }

    @staticmethod
    def get_scoring_breakdown(cv_text: str, job_type: str) -> Dict:
        """
        Get detailed scoring breakdown untuk debugging dan analysis
        """
        if job_type not in AstraScoringService.JOB_REQUIREMENTS:
            return {"error": "Job type tidak valid"}
        
        requirements = AstraScoringService.JOB_REQUIREMENTS[job_type]
        cv_text_lower = cv_text.lower()
        
        breakdown = {
            "job_requirements_breakdown": [],
            "nice_to_have_breakdown": [],
            "wajib_breakdown": {}
        }
        
        # Job Requirements Breakdown
        for i, requirement in enumerate(requirements["job_requirements"]):
            keyword_groups = requirement.split()
            matched_details = []
            
            for keyword_group in keyword_groups:
                group_keywords = keyword_group.split()
                group_matches = [kw for kw in group_keywords if kw in cv_text_lower]
                matched_details.append({
                    "group": keyword_group,
                    "matches": group_matches,
                    "matched_count": len(group_matches),
                    "total_keywords": len(group_keywords)
                })
            
            total_matched_groups = sum(1 for detail in matched_details if detail["matched_count"] > 0)
            fulfilled = total_matched_groups >= len(keyword_groups) * 0.5
            
            breakdown["job_requirements_breakdown"].append({
                "requirement": requirement,
                "matched_details": matched_details,
                "total_matched_groups": total_matched_groups,
                "total_groups": len(keyword_groups),
                "fulfilled": fulfilled
            })
        
        # Nice to Have Breakdown
        for item in requirements["nice_to_have"]:
            found = item in cv_text_lower
            item_words = item.split()
            partial_match = len(item_words) > 1 and any(word in cv_text_lower for word in item_words)
            
            breakdown["nice_to_have_breakdown"].append({
                "item": item,
                "found": found,
                "partial_match": partial_match and not found
            })
        
        return breakdown