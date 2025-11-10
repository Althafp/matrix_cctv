"""
Camera Image Analyzer with OpenAI GPT-4o
Analyzes camera images based on dynamic user queries
"""

import os
import base64
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import concurrent.futures
from tqdm import tqdm
from gcs_storage import get_gcs_manager

# Load environment variables
load_dotenv()

class CameraImageAnalyzer:
    def __init__(self, images_dir="camera_images", max_workers=5, excel_file="13data.xlsx"):
        """
        Initialize the Camera Image Analyzer
        
        Args:
            images_dir: Directory containing camera images (or GCS prefix)
            max_workers: Number of concurrent image analysis threads
            excel_file: Excel file with camera metadata (IP, location, lat/long, etc.)
        """
        self.images_dir = Path(images_dir)
        self.max_workers = max_workers
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Verify API key
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY not found in .env file!")
        
        # Initialize GCS manager
        self.gcs_manager = get_gcs_manager()
        self.use_gcs = self.gcs_manager.use_gcs
        
        # Load camera metadata from Excel
        self.camera_metadata = self.load_camera_metadata(excel_file)
        
        # Results storage
        self.analysis_results = []
        self.summary_report = {}
        
        # If using GCS, use direct URL mode (ZERO downloads!)
        if self.use_gcs:
            print(f"\n☁️  GCS Storage Mode - ZERO DOWNLOAD! 🚀")
            print(f"📦 Bucket: {self.gcs_manager.bucket_name}")
            print(f"📂 Prefix: {images_dir}/")
            print(f"⚡ OpenAI fetches images directly from GCS URLs")
            print(f"💾 NO downloads to server - ZERO storage used!")
            
            # Just list images (no download)
            image_list = self.gcs_manager.list_images(
                prefix=f"{images_dir}/" if not str(images_dir).endswith('/') else images_dir
            )
            if image_list:
                print(f"✅ Found {len(image_list)} images in GCS bucket\n")
                self.gcs_image_list = image_list
            else:
                print(f"⚠️  No images found in GCS bucket with prefix '{images_dir}/'\n")
                self.gcs_image_list = []
            
            self.cached_image_paths = None  # No downloads at all!
        else:
            print(f"\n📁 Local Storage Mode")
            self.cached_image_paths = None
            self.gcs_image_list = []
        
    def load_camera_metadata(self, excel_file: str) -> dict:
        """Load camera metadata from Excel file and index by IP"""
        try:
            import pandas as pd
            df = pd.read_excel(excel_file)
            
            print(f"\n📋 Loading {excel_file}...")
            print(f"   Columns: {df.columns.tolist()}")
            print(f"   Total rows: {len(df)}")
            
            # Clean column names
            df.columns = df.columns.str.strip()
            
            # Create dictionary indexed by Camera IP
            metadata_dict = {}
            skipped = 0
            
            for idx, row in df.iterrows():
                ip = str(row.get('CAMERA IP', '')).strip()
                
                # Skip empty or invalid IPs
                if not ip or ip == 'nan' or ip == 'None':
                    skipped += 1
                    continue
                    
                metadata_dict[ip] = {
                    'old_district': str(row.get('Old DISTRICT', 'Unknown')).strip(),
                    'new_district': str(row.get('NEW DISTRICT', 'Unknown')).strip(),
                    'mandal': str(row.get('MANDAL', 'Unknown')).strip(),
                    'location_name': str(row.get('Location Name', 'Unknown')).strip(),
                    'latitude': str(row.get('LATITUDE', '')).strip(),
                    'longitude': str(row.get('LONGITUDE', '')).strip(),
                    'camera_type': str(row.get('TYPE OF CAMERA', 'Unknown')).strip(),
                    'analytics_type': str(row.get('TYPE OF Analytics', 'Unknown')).strip()
                }
            
            print(f"✓ Loaded metadata for {len(metadata_dict)} cameras from {excel_file}")
            if skipped > 0:
                print(f"   (Skipped {skipped} rows with missing IPs)")
            
            # Show first 3 IPs as sample
            sample_ips = list(metadata_dict.keys())[:3]
            if sample_ips:
                print(f"   Sample IPs: {sample_ips}")
            
            return metadata_dict
        except Exception as e:
            print(f"⚠️ Could not load camera metadata from {excel_file}: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def encode_image(self, image_path: Path) -> str:
        """Encode image to base64 for OpenAI API"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def get_image_url_or_base64(self, image_path):
        """
        Get image as URL (if GCS) or base64 (if local)
        OpenAI can fetch directly from URL - no download needed!
        
        Args:
            image_path: Path object or GCS blob name (string)
            
        Returns:
            Tuple of (url_or_base64, is_url)
        """
        # If using GCS and image_path is a string (blob name)
        if self.use_gcs and isinstance(image_path, str):
            # Generate signed URL (valid for 1 hour)
            signed_url = self.gcs_manager.get_image_url(image_path, expiration_minutes=60)
            if signed_url:
                return (signed_url, True)  # Return URL, no download!
        
        # Fallback: download and encode
        if isinstance(image_path, str):
            actual_path = self.gcs_manager.get_image_as_path_object(image_path)
            if actual_path:
                return (self.encode_image(actual_path), False)
        else:
            return (self.encode_image(image_path), False)
        
        return (None, False)
    
    def extract_ip_from_filename(self, filename: str) -> str:
        """Extract camera IP from image filename"""
        # Filename format: {Location_Name}_{IP_octet1}_{IP_octet2}_{IP_octet3}_{IP_octet4}_{date}_{time}.jpg
        # Example: Adavivaram_Junction_10_242_6_175_20251108_133919.jpg
        # IP: 10.242.6.175
        
        parts = filename.replace('.jpg', '').replace('.jpeg', '').split('_')
        
        if len(parts) >= 6:
            # Last 6 parts are: IP_octet1, IP_octet2, IP_octet3, IP_octet4, date, time
            ip = f"{parts[-6]}.{parts[-5]}.{parts[-4]}.{parts[-3]}"
            
            # Debug: Print first extraction
            if not hasattr(self, '_first_ip_extracted'):
                self._first_ip_extracted = True
                print(f"\n🔍 DEBUG: Extracting IP from filename")
                print(f"   Filename: {filename}")
                print(f"   Parts: {parts}")
                print(f"   Last 6 parts: {parts[-6:]}")
                print(f"   Extracted IP: {ip}")
            
            return ip
        
        print(f"⚠️ Could not extract IP from {filename} (only {len(parts)} parts)")
        return "Unknown"
    
    def get_camera_metadata(self, camera_ip: str) -> dict:
        """Get camera metadata from Excel data by IP"""
        # Try exact match first
        if camera_ip in self.camera_metadata:
            return self.camera_metadata[camera_ip]
        
        # Try with stripped spaces (in case of formatting issues)
        camera_ip_clean = camera_ip.strip()
        if camera_ip_clean in self.camera_metadata:
            return self.camera_metadata[camera_ip_clean]
        
        # Debug: Print what we're looking for vs what exists
        if not hasattr(self, '_debug_printed'):
            self._debug_printed = True
            print(f"\n⚠️ DEBUG: Looking for IP '{camera_ip}' but not found in Excel")
            print(f"   Total IPs in Excel: {len(self.camera_metadata)}")
            if self.camera_metadata:
                sample_keys = list(self.camera_metadata.keys())[:5]
                print(f"   Sample IPs from Excel: {sample_keys}")
                # Check if IP exists with different formatting
                matching = [ip for ip in self.camera_metadata.keys() if camera_ip in ip or ip in camera_ip]
                if matching:
                    print(f"   Similar IPs found: {matching[:3]}")
        
        # Return default values if IP not found
        return {
            'old_district': 'Unknown',
            'new_district': 'Unknown',
            'mandal': 'Unknown',
            'location_name': 'Unknown',
            'latitude': '',
            'longitude': '',
            'camera_type': 'Unknown',
            'analytics_type': 'Unknown'
        }
    
    def analyze_user_query(self, user_query: str) -> Dict[str, Any]:
        """
        Analyze user query to understand what to look for in images
        
        Args:
            user_query: User's question about the images
            
        Returns:
            Dictionary with query analysis
        """
        print("\n🔍 Analyzing your query...")
        
        prompt = f"""You are an expert at understanding queries about traffic camera/CCTV images.

User Query: "{user_query}"

Analyze this query and provide a structured response in JSON format with the following fields:
1. "search_objective": What specifically to look for in images (be very specific)
2. "count_required": true/false - Does the query require counting something?
3. "entity_type": What is being searched for (e.g., "pedestrians", "vehicles", "poles", "signs", etc.)
4. "detection_criteria": Specific criteria to identify if an image matches the query
5. "data_to_collect": What specific information to extract from each matching image
6. "response_format": How the final answer should be structured

Respond ONLY with valid JSON, no other text."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a query analysis expert. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            analysis = json.loads(response.choices[0].message.content)
            print(f"✓ Query understood: Looking for '{analysis.get('entity_type', 'items')}'")
            return analysis
            
        except Exception as e:
            print(f"⚠ Error analyzing query: {e}")
            # Fallback simple analysis
            return {
                "search_objective": user_query,
                "count_required": True,
                "entity_type": "items",
                "detection_criteria": user_query,
                "data_to_collect": "presence and count",
                "response_format": "List locations with counts"
            }
    
    def process_contextual_query(self, user_query: str, context: str, previous_results: Dict) -> Dict[str, Any]:
        """
        Process a follow-up query using context from previous queries
        
        Args:
            user_query: Current user query
            context: Context string from previous conversation
            previous_results: Results from previous analysis
            
        Returns:
            Response dictionary
        """
        print(f"\n🔗 Processing contextual query (using previous results)...")
        
        # Build a comprehensive prompt with context
        prompt = f"""{context}

CURRENT USER QUERY: "{user_query}"

Based on the previous conversation and results above, please provide a comprehensive answer to the user's current query.

Available data from previous analysis:
- Total images analyzed: {previous_results.get('total_images', 0)}
- Matches found: {previous_results.get('matches_found', 0)}
- Detailed results with location names, coordinates, camera IPs, and analysis

Instructions:
1. Understand what the user is asking based on context
2. If they reference "these", "those", "them" - they mean the previous results
3. Use the detailed results to answer their query
4. Provide specific data (locations, coordinates, counts) as relevant
5. Format your response clearly

Respond with a comprehensive answer that directly addresses their query."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant analyzing CCTV camera data. Use the conversation context to answer follow-up questions."},
                    {"role": "user", "content": prompt + "\n\nPrevious Results Data:\n" + json.dumps(previous_results, indent=2)}
                ],
                temperature=0.5
            )
            
            answer = response.choices[0].message.content
            
            # Build response in same format as regular analysis
            detailed_results = previous_results.get('detailed_results', [])
            
            return {
                'total_images': previous_results.get('total_images', 0),
                'matches_found': previous_results.get('matches_found', 0),
                'unique_locations': previous_results.get('unique_locations', 0),
                'detailed_results': detailed_results,
                'final_answer': answer,
                'is_contextual': True  # Flag to indicate this used context
            }
            
        except Exception as e:
            print(f"❌ Error processing contextual query: {e}")
            return {
                'total_images': 0,
                'matches_found': 0,
                'unique_locations': 0,
                'detailed_results': [],
                'final_answer': f"Error processing query: {str(e)}",
                'error': str(e)
            }
    
    def analyze_single_image(self, image_path, query_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a single image based on the query
        
        Args:
            image_path: Path to the image or GCS blob name (string)
            query_analysis: Analysis of the user query
            
        Returns:
            Dictionary with image analysis results
        """
        # Get filename
        if isinstance(image_path, str):
            filename = Path(image_path).name
        else:
            filename = image_path.name
        
        # Extract IP from filename
        camera_ip = self.extract_ip_from_filename(filename)
        
        # Get camera metadata from Excel
        metadata = self.get_camera_metadata(camera_ip)
        
        try:
            # Get image as URL (GCS) or base64 (local)
            image_data, is_url = self.get_image_url_or_base64(image_path)
            
            if not image_data:
                return {
                    "image_name": filename,
                    "match": False,
                    "status": "error",
                    "error": "Failed to get image"
                }
            
            # Create specific prompt based on query analysis
            search_objective = query_analysis.get('search_objective', '')
            entity_type = query_analysis.get('entity_type', 'items')
            detection_criteria = query_analysis.get('detection_criteria', '')
            data_to_collect = query_analysis.get('data_to_collect', '')
            
            prompt = f"""Analyze this CCTV/traffic camera image carefully.

SEARCH OBJECTIVE: {search_objective}
LOOKING FOR: {entity_type}
DETECTION CRITERIA: {detection_criteria}

Please analyze the image and provide a JSON response with:
1. "match": true/false - Does this image match the search criteria?
2. "count": Number of {entity_type} found (0 if none)
3. "description": Brief description of what you see relevant to the query
4. "details": Specific details about the {entity_type} found
5. "confidence": Your confidence level (high/medium/low)
6. "additional_observations": Any other relevant observations

Respond ONLY with valid JSON."""

            # Build image URL object based on type
            if is_url:
                # Direct URL from GCS - OpenAI fetches directly!
                image_url_obj = {
                    "url": image_data,
                    "detail": "high"
                }
            else:
                # Base64 encoded (local file)
                image_url_obj = {
                    "url": f"data:image/jpeg;base64,{image_data}",
                    "detail": "high"
                }

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": image_url_obj
                            }
                        ]
                    }
                ],
                max_tokens=1000,
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            analysis = json.loads(response.choices[0].message.content)
            
            return {
                "image_name": filename,
                "camera_ip": camera_ip,
                "old_district": metadata['old_district'],
                "new_district": metadata['new_district'],
                "mandal": metadata['mandal'],
                "location_name": metadata['location_name'],
                "latitude": metadata['latitude'],
                "longitude": metadata['longitude'],
                "camera_type": metadata['camera_type'],
                "analytics_type": metadata['analytics_type'],
                "match": analysis.get("match", False),
                "count": analysis.get("count", 0),
                "description": analysis.get("description", ""),
                "details": analysis.get("details", ""),
                "confidence": analysis.get("confidence", "medium"),
                "additional_observations": analysis.get("additional_observations", ""),
                "status": "success"
            }
            
        except Exception as e:
            return {
                "image_name": filename,
                "camera_ip": camera_ip,
                "old_district": metadata['old_district'],
                "new_district": metadata['new_district'],
                "mandal": metadata['mandal'],
                "location_name": metadata['location_name'],
                "latitude": metadata['latitude'],
                "longitude": metadata['longitude'],
                "camera_type": metadata['camera_type'],
                "analytics_type": metadata['analytics_type'],
                "match": False,
                "count": 0,
                "description": f"Error analyzing image: {str(e)}",
                "status": "error",
                "error": str(e)
            }
    
    def analyze_all_images(self, user_query: str) -> List[Dict[str, Any]]:
        """
        Analyze all images based on user query
        
        Args:
            user_query: User's question
            
        Returns:
            List of analysis results for all images
        """
        # First, analyze the query
        query_analysis = self.analyze_user_query(user_query)
        
        # Get all image files (GCS list or local files)
        if self.use_gcs and self.gcs_image_list:
            # Use GCS image list (direct URL mode - ZERO downloads!)
            print(f"\n📸 Analyzing {len(self.gcs_image_list)} images from GCS")
            print(f"🌐 OpenAI fetching directly from GCS URLs - NO downloads!")
            image_files = self.gcs_image_list  # Just blob names
        else:
            # Use local images
            image_files = list(self.images_dir.glob("*.jpg")) + list(self.images_dir.glob("*.jpeg"))
            print(f"\n📸 Found {len(image_files)} images in local directory")
        
        if not image_files:
            print(f"⚠ No images found!")
            if self.use_gcs:
                print(f"   Checked GCS bucket: {self.gcs_manager.bucket_name}")
                print(f"   Prefix: {self.images_dir}/")
            else:
                print(f"   Checked local directory: {self.images_dir}")
            return []
        
        print(f"🚀 Starting analysis with {self.max_workers} concurrent workers...\n")
        
        # Analyze images concurrently with progress bar
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_image = {
                executor.submit(self.analyze_single_image, img, query_analysis): img 
                for img in image_files
            }
            
            # Process with progress bar
            with tqdm(total=len(image_files), desc="Analyzing images", unit="img") as pbar:
                for future in concurrent.futures.as_completed(future_to_image):
                    result = future.result()
                    results.append(result)
                    
                    # Show status
                    if result['match']:
                        tqdm.write(f"  ✓ Match: {result['location_name']} ({result['mandal']}, {result['new_district']}) - IP: {result['camera_ip']} (Count: {result['count']})")
                    
                    pbar.update(1)
        
        self.analysis_results = results
        return results
    
    def generate_final_report(self, user_query: str, query_analysis: Dict[str, Any]) -> str:
        """
        Generate final report using hybrid approach:
        - GPT generates summary/insights (small prompt - no token limits!)
        - Programmatically append detailed location list (handles unlimited results)
        
        Args:
            user_query: Original user query
            query_analysis: Query analysis results
            
        Returns:
            Formatted final report
        """
        print("\n📊 Generating comprehensive report...")
        
        # Prepare data summary
        matching_results = [r for r in self.analysis_results if r['match'] and r['status'] == 'success']
        total_count = sum(r['count'] for r in matching_results if isinstance(r['count'], int))
        
        # Prepare aggregated statistics (small, for GPT - NO TOKEN LIMIT ISSUES!)
        summary_stats = {
            "total_images_analyzed": len(self.analysis_results),
            "matching_locations": len(matching_results),
            "total_count": total_count,
            "districts": list(set(r['new_district'] for r in matching_results)),
            "top_locations": sorted(
                [(r['location_name'], r['count']) for r in matching_results if isinstance(r['count'], int)],
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }
        
        print(f"   📍 {summary_stats['matching_locations']} matching locations found")
        print(f"   🌍 Districts: {', '.join(summary_stats['districts'][:3])}{'...' if len(summary_stats['districts']) > 3 else ''}")
        
        # Generate summary and insights with GPT (SMALL prompt - only stats, not all details!)
        prompt = f"""Query: "{user_query}"

Statistics:
- Total images analyzed: {summary_stats['total_images_analyzed']}
- Matching locations found: {summary_stats['matching_locations']}
- Total count: {summary_stats['total_count']}
- Districts: {', '.join(summary_stats['districts'])}
- Top 10 locations: {summary_stats['top_locations']}

Generate a concise report with:
1. **Introduction** (2-3 sentences addressing the query)
2. **Key Findings** (4-6 bullet points of insights/patterns)
3. **Conclusion** (2-3 sentences with recommendations)

Keep it brief and professional - detailed location data will be appended separately.
Make it conversational as if presenting to a city official."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert analyst generating reports from CCTV camera analysis data."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=800
            )
            
            gpt_summary = response.choices[0].message.content
            print("   ✅ GPT summary generated")
        
        except Exception as e:
            print(f"   ⚠️ GPT summary failed: {e}, using default")
            gpt_summary = f"""
**Introduction**

Analysis completed for: "{user_query}"

**Key Findings**

- Total images analyzed: {summary_stats['total_images_analyzed']}
- Matching locations: {summary_stats['matching_locations']}
- Total count: {summary_stats['total_count']}
- Districts covered: {', '.join(summary_stats['districts'])}

**Conclusion**

Detailed location analysis provided below.
"""
        
        # Programmatically build detailed location section (NO GPT, NO TOKEN LIMITS!)
        print("   📝 Building detailed location section...")
        detailed_section = self._build_detailed_locations_section(matching_results, user_query)
        print(f"   ✅ Detailed section built ({len(matching_results)} locations)")
        
        # Combine: GPT summary + Programmatic details
        final_report = f"""{gpt_summary}

---

{detailed_section}

---

**Analysis Statistics**

- Total Images Analyzed: {len(self.analysis_results)}
- Matching Locations: {len(matching_results)}
- Success Rate: {round((len(matching_results) / len(self.analysis_results)) * 100, 1) if len(self.analysis_results) > 0 else 0}%
"""
        
        return final_report
    
    def _build_detailed_locations_section(self, matching_results: list, user_query: str) -> str:
        """
        Build detailed location section programmatically (no GPT, no token limits)
        This can handle 1000+ results without any issues!
        """
        if not matching_results:
            return "**Detailed Analysis by Location**\n\nNo matching locations found."
        
        section = f"**Detailed Analysis by Location**\n\n"
        section += f"Found {len(matching_results)} locations matching your query.\n\n"
        
        # Group by district for better organization
        by_district = {}
        for result in matching_results:
            district = result['new_district']
            if district not in by_district:
                by_district[district] = []
            by_district[district].append(result)
        
        # Build location entries
        for district, locations in sorted(by_district.items()):
            section += f"### {district} ({len(locations)} locations)\n\n"
            
            for idx, result in enumerate(locations, 1):
                section += f"**{idx}. {result['location_name']}**\n\n"
                section += f"- 📍 **District:** {result['new_district']}\n"
                section += f"- 🏘️ **Mandal:** {result['mandal']}\n"
                section += f"- 📹 **Camera IP:** {result['camera_ip']}\n"
                
                if result.get('latitude') and result.get('longitude'):
                    section += f"- 🌍 **Coordinates:** {result['latitude']}, {result['longitude']}\n"
                
                section += f"- 📊 **Count:** {result['count']}\n"
                section += f"- ✅ **Confidence:** {result['confidence']}\n"
                section += f"- 📝 **Details:** {result['description']}\n"
                
                if result.get('details'):
                    section += f"- 🔍 **Observations:** {result['details']}\n"
                
                section += "\n"
        
        return section
    
    def _generate_fallback_report(self, user_query: str, summary_stats: Dict) -> str:
        """Generate simple fallback report if LLM fails"""
        report = f"""
{'='*80}
ANALYSIS REPORT
{'='*80}

Query: {user_query}

SUMMARY:
- Total images analyzed: {summary_stats['total_images_analyzed']}
- Matching locations: {summary_stats['matching_locations']}
- Total count: {summary_stats['total_count']}
- Districts: {', '.join(summary_stats.get('districts', []))}

"""
        # Add programmatic detailed section
        matching_results = [r for r in self.analysis_results if r['match'] and r['status'] == 'success']
        detailed_section = self._build_detailed_locations_section(matching_results, user_query)
        
        report += detailed_section
        
        return report
    
    def save_results(self, user_query: str, final_report: str):
        """Save analysis results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("analysis_results")
        output_dir.mkdir(exist_ok=True)
        
        # Save detailed JSON
        json_file = output_dir / f"analysis_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                "query": user_query,
                "timestamp": timestamp,
                "results": self.analysis_results,
                "report": final_report
            }, f, indent=2, ensure_ascii=False)
        
        # Save readable report
        report_file = output_dir / f"report_{timestamp}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"QUERY: {user_query}\n")
            f.write(f"TIMESTAMP: {timestamp}\n")
            f.write("="*80 + "\n\n")
            f.write(final_report)
        
        print(f"\n💾 Results saved:")
        print(f"   - JSON: {json_file}")
        print(f"   - Report: {report_file}")
    
    def run_analysis(self, user_query: str, save_to_file: bool = True) -> str:
        """
        Main workflow: Run complete analysis
        
        Args:
            user_query: User's question about the images
            save_to_file: Whether to save results to files
            
        Returns:
            Final report as string
        """
        print("\n" + "="*80)
        print("CAMERA IMAGE ANALYZER - GPT-4o Vision")
        print("="*80)
        print(f"Query: {user_query}")
        print("="*80)
        
        # Step 1: Analyze query
        query_analysis = self.analyze_user_query(user_query)
        
        # Step 2: Analyze all images
        self.analyze_all_images(user_query)
        
        # Step 3: Generate final report
        final_report = self.generate_final_report(user_query, query_analysis)
        
        # Step 4: Save results
        if save_to_file:
            self.save_results(user_query, final_report)
        
        return final_report


def main():
    """Interactive main function"""
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║              CAMERA IMAGE ANALYZER WITH GPT-4o VISION                         ║
║                     Analyze camera images with AI                             ║
╚═══════════════════════════════════════════════════════════════════════════════╝
""")
    
    # Check for .env file
    if not os.path.exists('.env'):
        print("⚠ .env file not found!")
        print("Please create a .env file with your OpenAI API key:")
        print("  OPENAI_API_KEY=your_api_key_here")
        return
    
    try:
        # Initialize analyzer
        analyzer = CameraImageAnalyzer(
            images_dir="test",
            max_workers=5  # Adjust based on your OpenAI rate limits
        )
        
        print("\nExample queries:")
        print("  • How many junctions have pedestrians crossing the road?")
        print("  • Which locations have street light poles visible?")
        print("  • How many vehicles are present at each location?")
        print("  • Which areas show heavy traffic congestion?")
        print("  • Are there any accidents or incidents visible?")
        print("  • Count the number of two-wheelers in each location")
        
        # Get user query
        print("\n" + "-"*80)
        user_query = input("\n🔍 Enter your query: ").strip()
        
        if not user_query:
            print("⚠ No query provided!")
            return
        
        # Run analysis
        final_report = analyzer.run_analysis(user_query, save_to_file=True)
        
        # Display report
        print("\n" + "="*80)
        print("FINAL REPORT")
        print("="*80)
        print(final_report)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

