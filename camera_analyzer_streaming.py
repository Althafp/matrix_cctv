"""
Streaming Camera Image Analyzer
Yields results as they are analyzed for real-time UI updates
"""

import os
import base64
import json
from pathlib import Path
from typing import Dict, Any, Generator
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import concurrent.futures
import time
from gcs_storage import get_gcs_manager

load_dotenv()


class StreamingCameraAnalyzer:
    """Analyzer that streams results as they complete"""
    
    def __init__(self, images_dir="camera_images", max_workers=5, excel_file="13data.xlsx"):
        self.images_dir = Path(images_dir)
        self.max_workers = max_workers
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY not found in .env file!")
        
        # Initialize GCS manager
        self.gcs_manager = get_gcs_manager()
        self.use_gcs = self.gcs_manager.use_gcs
        
        # Load camera metadata
        self.camera_metadata = self.load_camera_metadata(excel_file)
        self.analysis_results = []
        
        # If using GCS, use lazy loading (list only, no download)
        if self.use_gcs:
            # Just list images (no download)
            self.gcs_image_list = self.gcs_manager.list_images(
                prefix=f"{images_dir}/" if not str(images_dir).endswith('/') else images_dir
            )
            self.cached_image_paths = None
        else:
            self.gcs_image_list = []
            self.cached_image_paths = None
    
    def load_camera_metadata(self, excel_file: str) -> dict:
        """Load camera metadata from Excel file"""
        try:
            import pandas as pd
            df = pd.read_excel(excel_file)
            
            df.columns = df.columns.str.strip()
            metadata_dict = {}
            skipped = 0
            
            for idx, row in df.iterrows():
                ip = str(row.get('CAMERA IP', '')).strip()
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
            
            return metadata_dict
        
        except Exception as e:
            print(f"⚠️ Could not load Excel metadata: {e}")
            return {}
    
    def extract_ip_from_filename(self, filename: str) -> str:
        """Extract IP from filename"""
        parts = filename.replace('.jpg', '').replace('.jpeg', '').split('_')
        if len(parts) >= 6:
            ip = f"{parts[-6]}.{parts[-5]}.{parts[-4]}.{parts[-3]}"
            return ip
        return "Unknown"
    
    def get_camera_metadata(self, camera_ip: str) -> dict:
        """Get metadata for a camera IP"""
        if camera_ip in self.camera_metadata:
            return self.camera_metadata[camera_ip]
        
        camera_ip_clean = camera_ip.strip()
        if camera_ip_clean in self.camera_metadata:
            return self.camera_metadata[camera_ip_clean]
        
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
    
    def encode_image(self, image_path: Path) -> str:
        """Encode image to base64"""
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
    
    def analyze_single_image(self, image_path, query_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single image (supports both local paths and GCS blob names)"""
        try:
            # Get filename
            if isinstance(image_path, str):
                filename = Path(image_path).name
            else:
                filename = image_path.name
            
            # Extract metadata
            camera_ip = self.extract_ip_from_filename(filename)
            metadata = self.get_camera_metadata(camera_ip)
            
            # Get image as URL (GCS) or base64 (local)
            image_data, is_url = self.get_image_url_or_base64(image_path)
            
            if not image_data:
                return {
                    'filename': filename,
                    'match': False,
                    'status': 'error',
                    'error': 'Failed to get image'
                }
            
            # Create prompt
            prompt = f"""Analyze this CCTV camera image for: {query_analysis['search_criteria']}

Location: {metadata['location_name']}
District: {metadata['new_district']}
Mandal: {metadata['mandal']}

Task: {query_analysis['analysis_type']}

Respond in JSON:
{{
    "match": true/false,
    "count": number or "N/A",
    "description": "brief description",
    "confidence": "high/medium/low",
    "details": "specific observations"
}}"""
            
            # Build image URL object based on type
            if is_url:
                # Direct URL from GCS - OpenAI fetches directly!
                image_url_obj = {
                    "url": image_data,
                    "detail": "auto"
                }
            else:
                # Base64 encoded (local file)
                image_url_obj = {
                    "url": f"data:image/jpeg;base64,{image_data}",
                    "detail": "auto"
                }
            
            # Call OpenAI API
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
                max_tokens=500,
                temperature=0.3
            )
            
            # Parse response
            content = response.choices[0].message.content
            
            # Try to extract JSON
            if '{' in content and '}' in content:
                json_start = content.index('{')
                json_end = content.rindex('}') + 1
                json_str = content[json_start:json_end]
                analysis = json.loads(json_str)
            else:
                analysis = {
                    "match": False,
                    "count": "N/A",
                    "description": content,
                    "confidence": "low",
                    "details": "Could not parse response"
                }
            
            # Build result
            result = {
                'filename': filename,
                'camera_ip': camera_ip,
                **metadata,
                'match': analysis.get('match', False),
                'count': analysis.get('count', 'N/A'),
                'description': analysis.get('description', ''),
                'confidence': analysis.get('confidence', 'unknown'),
                'details': analysis.get('details', ''),
                'status': 'success',
                'timestamp': datetime.now().isoformat()
            }
            
            return result
        
        except Exception as e:
            filename = Path(image_path).name if isinstance(image_path, str) else image_path.name
            return {
                'filename': filename,
                'camera_ip': 'Unknown',
                'match': False,
                'count': 'N/A',
                'description': f'Error: {str(e)}',
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def analyze_user_query(self, user_query: str) -> Dict[str, Any]:
        """Analyze user query to understand what to look for"""
        prompt = f"""Analyze this query: "{user_query}"

Respond in JSON:
{{
    "search_criteria": "what to look for",
    "analysis_type": "counting/detection/classification",
    "category": "vehicles/people/violations/infrastructure"
}}"""
        
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.3
        )
        
        content = response.choices[0].message.content
        
        if '{' in content and '}' in content:
            json_start = content.index('{')
            json_end = content.rindex('}') + 1
            json_str = content[json_start:json_end]
            return json.loads(json_str)
        
        return {
            "search_criteria": user_query,
            "analysis_type": "detection",
            "category": "general"
        }
    
    def stream_analysis(self, user_query: str) -> Generator[Dict[str, Any], None, None]:
        """
        Stream analysis results as they complete
        
        Yields:
            Dict with 'type' and 'data' for each event
        """
        # Step 1: Send start event
        yield {
            'type': 'start',
            'data': {
                'message': 'Starting analysis...',
                'query': user_query
            }
        }
        
        # Step 2: Analyze query
        yield {
            'type': 'log',
            'data': {'message': '🔍 Analyzing your query...'}
        }
        
        query_analysis = self.analyze_user_query(user_query)
        
        yield {
            'type': 'query_analysis',
            'data': {
                'message': f"Query understood: Looking for '{query_analysis['search_criteria']}'",
                'analysis': query_analysis
            }
        }
        
        # Step 3: Get image files (GCS list or local)
        if self.use_gcs and self.gcs_image_list:
            image_files = self.gcs_image_list  # Just blob names
            yield {
                'type': 'log',
                'data': {'message': f'☁️  Analyzing {len(image_files)} images from GCS (direct URLs - ZERO downloads!)'}
            }
        else:
        image_files = list(self.images_dir.glob("*.jpg")) + list(self.images_dir.glob("*.jpeg"))
            yield {
                'type': 'log',
                'data': {'message': f'📂 Found {len(image_files)} images in local directory'}
            }
        
        if not image_files:
            error_msg = 'No images found!'
            if self.use_gcs:
                error_msg += f" (Checked GCS bucket: {self.gcs_manager.bucket_name}, Prefix: {self.images_dir}/)"
            else:
                error_msg += f" (Checked local directory: {self.images_dir})"
            
            yield {
                'type': 'error',
                'data': {'message': error_msg}
            }
            return
        
        yield {
            'type': 'log',
            'data': {'message': f'🚀 Starting analysis with {self.max_workers} concurrent workers...'}
        }
        
        # Step 4: Analyze images with streaming
        results = []
        processed_count = 0
        match_count = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_image = {
                executor.submit(self.analyze_single_image, img, query_analysis): img 
                for img in image_files
            }
            
            # Process as they complete
            for future in concurrent.futures.as_completed(future_to_image):
                result = future.result()
                results.append(result)
                processed_count += 1
                
                # Send progress update
                yield {
                    'type': 'progress',
                    'data': {
                        'current': processed_count,
                        'total': len(image_files),
                        'percent': int((processed_count / len(image_files)) * 100)
                    }
                }
                
                # Send log for this image
                yield {
                    'type': 'log',
                    'data': {
                        'message': f"📷 Processed: {result['filename']}"
                    }
                }
                
                # If match, send result immediately!
                if result['match']:
                    match_count += 1
                    yield {
                        'type': 'match',
                        'data': {
                            'message': f"✅ Match #{match_count}: {result['location_name']} ({result['mandal']}, {result['new_district']}) - IP: {result['camera_ip']} (Count: {result['count']})",
                            'result': result
                        }
                    }
        
        # Step 5: Send summary
        self.analysis_results = results
        matching_results = [r for r in results if r['match']]
        
        yield {
            'type': 'log',
            'data': {'message': f'\n✅ Analysis complete!'}
        }
        
        yield {
            'type': 'log',
            'data': {'message': f'📊 Total analyzed: {len(results)}'}
        }
        
        yield {
            'type': 'log',
            'data': {'message': f'✅ Matches found: {len(matching_results)}'}
        }
        
        # Step 6: Generate report
        yield {
            'type': 'log',
            'data': {'message': '📝 Generating comprehensive report...'}
        }
        
        final_report = self.generate_final_report(user_query, query_analysis)
        
        # Step 7: Send final results
        yield {
            'type': 'complete',
            'data': {
                'total_images': len(results),
                'matches_found': len(matching_results),
                'unique_locations': len(set(r['location_name'] for r in matching_results)),
                'detailed_results': results,
                'final_answer': final_report,
                'is_contextual': False
            }
        }
    
    def generate_final_report(self, user_query: str, query_analysis: Dict[str, Any]) -> str:
        """
        Generate final report using hybrid approach:
        - GPT generates summary/insights (small prompt)
        - Programmatically append detailed location list (no token limit)
        """
        matching_results = [r for r in self.analysis_results if r['match'] and r['status'] == 'success']
        total_count = sum(r['count'] for r in matching_results if isinstance(r['count'], int))
        
        # Prepare aggregated statistics (small, for GPT)
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
        
        # Generate summary and insights with GPT (SMALL prompt - no full details)
        prompt = f"""Query: "{user_query}"

Statistics:
- Total images analyzed: {summary_stats['total_images_analyzed']}
- Matching locations found: {summary_stats['matching_locations']}
- Total count: {summary_stats['total_count']}
- Districts: {', '.join(summary_stats['districts'])}
- Top 10 locations: {summary_stats['top_locations']}

Generate a concise report with:
1. **Introduction** (2-3 sentences)
2. **Key Findings** (3-5 bullet points of insights/patterns)
3. **Conclusion** (2-3 sentences with recommendations)

Keep it brief - detailed location data will be appended separately."""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.7
            )
            
            gpt_summary = response.choices[0].message.content
        
        except Exception as e:
            print(f"⚠️ GPT summary failed: {e}, using default")
            gpt_summary = f"""
**Introduction**

Analysis completed for: "{user_query}"

**Key Findings**

- Total images analyzed: {summary_stats['total_images_analyzed']}
- Matching locations: {summary_stats['matching_locations']}
- Total count: {summary_stats['total_count']}

**Conclusion**

Detailed location analysis provided below.
"""
        
        # Programmatically build detailed location section (NO GPT, NO TOKEN LIMITS!)
        detailed_section = self._build_detailed_locations_section(matching_results, user_query)
        
        # Combine: GPT summary + Programmatic details
        final_report = f"""{gpt_summary}

---

{detailed_section}

---

**Analysis Statistics**

- Total Images Analyzed: {len(self.analysis_results)}
- Matching Locations: {len(matching_results)}
- Success Rate: {round((len(matching_results) / len(self.analysis_results)) * 100, 1)}%
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
                
                if result['latitude'] and result['longitude']:
                    section += f"- 🌍 **Coordinates:** {result['latitude']}, {result['longitude']}\n"
                
                section += f"- 📊 **Count:** {result['count']}\n"
                section += f"- ✅ **Confidence:** {result['confidence']}\n"
                section += f"- 📝 **Details:** {result['description']}\n"
                
                if result.get('details'):
                    section += f"- 🔍 **Observations:** {result['details']}\n"
                
                section += "\n"
        
        return section

