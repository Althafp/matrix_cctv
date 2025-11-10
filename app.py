"""
Flask Camera Analyzer - Web Application
Beautiful Bootstrap UI with session management
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory, send_file
from pathlib import Path
import json
from datetime import datetime
import os
from session_manager import SessionManager
from camera_analyzer import CameraImageAnalyzer
from camera_analyzer_streaming import StreamingCameraAnalyzer
from gcs_storage import get_gcs_manager
import secrets
import io

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'camera_images'

# Global managers
session_manager = SessionManager()
analyzers = {}  # Store analyzers per session
global_analyzer = None  # Global analyzer instance
gcs_manager = None  # GCS storage manager

# Auto-initialize analyzer on startup
def init_global_analyzer():
    """Initialize the global analyzer with default settings"""
    global global_analyzer, gcs_manager
    try:
        # Initialize GCS manager first
        gcs_manager = get_gcs_manager()
        images_dir = os.getenv('IMAGES_DIR', 'test')
        excel_file = os.getenv('EXCEL_FILE', '13data.xlsx')
        max_workers = int(os.getenv('MAX_WORKERS', '5'))
        
        print(f"\n{'='*60}")
        print("🚀 Initializing Camera Analyzer...")
        print(f"📁 Images Directory: {images_dir}")
        print(f"📊 Excel File: {excel_file}")
        print(f"⚙️  Max Workers: {max_workers}")
        
        global_analyzer = CameraImageAnalyzer(
            images_dir=images_dir,
            max_workers=max_workers,
            excel_file=excel_file
        )
        
        # Count available images
        images_path = Path(images_dir)
        if images_path.exists():
            image_count = len(list(images_path.glob("*.jpg")) + list(images_path.glob("*.jpeg")))
            print(f"✅ Found {image_count} images")
        else:
            print(f"⚠️  Warning: Images directory not found: {images_dir}")
        
        # Check Excel file
        excel_path = Path(excel_file)
        if excel_path.exists():
            print(f"✅ Excel file loaded successfully")
        else:
            print(f"⚠️  Warning: Excel file not found: {excel_file}")
        
        print("✅ Analyzer initialized successfully!")
        print(f"{'='*60}\n")
        return True
        
    except Exception as e:
        print(f"❌ Failed to initialize analyzer: {e}")
        import traceback
        traceback.print_exc()
        return False


def convert_paths_to_strings(obj):
    """
    Recursively convert all Path objects to strings for JSON serialization.
    """
    if isinstance(obj, Path):
        return str(obj)
    elif isinstance(obj, dict):
        return {key: convert_paths_to_strings(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_paths_to_strings(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_paths_to_strings(item) for item in obj)
    else:
        return obj


@app.route('/')
def index():
    """Main page"""
    # Initialize session if new
    if 'session_id' not in session:
        session['session_id'] = secrets.token_hex(16)
    
    # Get all sessions for sidebar
    all_sessions = session_manager.get_all_sessions()
    
    # Get current session if any
    current_session_id = session.get('current_analysis_session')
    current_session = None
    if current_session_id:
        current_session = session_manager.load_session(current_session_id)
    
    # Check analyzer status
    analyzer_ready = global_analyzer is not None
    
    # Get Google Maps API key from environment
    google_maps_api_key = os.getenv('GOOGLE_MAPS_API_KEY', '')
    
    # Get analyzer info if ready
    analyzer_info = {}
    if analyzer_ready:
        images_path = Path(global_analyzer.images_dir)
        if images_path.exists():
            image_count = len(list(images_path.glob("*.jpg")) + list(images_path.glob("*.jpeg")))
        else:
            image_count = 0
        
        analyzer_info = {
            'ready': True,
            'images_dir': global_analyzer.images_dir,
            'image_count': image_count,
            'max_workers': global_analyzer.max_workers
        }
    else:
        analyzer_info = {'ready': False}
    
    return render_template('index.html', 
                         all_sessions=all_sessions,
                         current_session=current_session,
                         analyzer_info=analyzer_info,
                         google_maps_api_key=google_maps_api_key)


@app.route('/check_config')
def check_config():
    """Check configuration status"""
    import os
    config_status = {
        'google_maps_api_key_exists': bool(os.getenv('GOOGLE_MAPS_API_KEY')),
        'google_maps_api_key_length': len(os.getenv('GOOGLE_MAPS_API_KEY', '')),
        'images_dir': os.getenv('IMAGES_DIR', 'test'),
        'excel_file': os.getenv('EXCEL_FILE', '13data.xlsx'),
        'max_workers': os.getenv('MAX_WORKERS', '5'),
        'env_file_exists': os.path.exists('.env')
    }
    return jsonify(config_status)


@app.route('/initialize_analyzer', methods=['POST'])
def initialize_analyzer():
    """Initialize the analyzer with settings"""
    data = request.json
    images_dir = data.get('images_dir', 'camera_images')
    excel_file = data.get('excel_file', '13data.xlsx')
    max_workers = int(data.get('max_workers', 5))
    
    try:
        analyzer = CameraImageAnalyzer(
            images_dir=images_dir,
            max_workers=max_workers,
            excel_file=excel_file
        )
        
        # Store analyzer in session
        sess_id = session['session_id']
        analyzers[sess_id] = analyzer
        
        return jsonify({
            'success': True,
            'message': 'Analyzer initialized successfully!'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 400


@app.route('/create_session', methods=['POST'])
def create_session():
    """Create a new analysis session"""
    sess_id = session_manager.create_session()
    session['current_analysis_session'] = sess_id
    
    return jsonify({
        'success': True,
        'session_id': sess_id,
        'message': 'New session created!'
    })


@app.route('/load_session/<session_id>')
def load_session(session_id):
    """Load an existing session"""
    sess = session_manager.load_session(session_id)
    if sess:
        session['current_analysis_session'] = session_id
        return jsonify({
            'success': True,
            'session': {
                'id': session_id,
                'title': sess['info']['title'],
                'queries': sess['conversation']['queries']
            }
        })
    return jsonify({'success': False, 'message': 'Session not found'}), 404


@app.route('/analyze_stream')
def analyze_stream():
    """Stream analysis results in real-time using Server-Sent Events"""
    query = request.args.get('query', '')
    
    if not query:
        return jsonify({'success': False, 'message': 'Query is required'}), 400
    
    # Get current session
    current_session_id = session.get('current_analysis_session')
    if not current_session_id:
        current_session_id = session_manager.create_session(query)
        session['current_analysis_session'] = current_session_id
    
    def generate():
        """Generator function for SSE"""
        try:
            # Initialize streaming analyzer
            streaming_analyzer = StreamingCameraAnalyzer(
                images_dir=global_analyzer.images_dir if global_analyzer else 'test',
                max_workers=global_analyzer.max_workers if global_analyzer else 5,
                excel_file='13data.xlsx'
            )
            
            # Stream analysis results
            for event in streaming_analyzer.stream_analysis(query):
                # Format as SSE
                yield f"data: {json.dumps(event)}\n\n"
            
            # Save final results to session
            if streaming_analyzer.analysis_results:
                matching_results = [r for r in streaming_analyzer.analysis_results if r['match']]
                
                results_dict = {
                    'total_images': len(streaming_analyzer.analysis_results),
                    'matches_found': len(matching_results),
                    'unique_locations': len(set(r['location_name'] for r in matching_results)),
                    'detailed_results': streaming_analyzer.analysis_results,
                    'final_answer': '',  # Report generated separately
                    'is_contextual': False
                }
                
                # Generate and add final report
                query_analysis = streaming_analyzer.analyze_user_query(query)
                results_dict['final_answer'] = streaming_analyzer.generate_final_report(query, query_analysis)
                
                # Save to session manager
                # First, load the session to make it current
                session_manager.load_session(current_session_id)
                
                # Then add the query
                session_manager.add_query(
                    query,
                    results_dict
                )
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            error_event = {
                'type': 'error',
                'data': {'message': f'Error: {str(e)}'}
            }
            yield f"data: {json.dumps(error_event)}\n\n"
    
    return app.response_class(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )


@app.route('/analyze', methods=['POST'])
def analyze():
    """Run analysis on images"""
    data = request.json
    query = data.get('query', '')
    use_batch = data.get('use_batch', False)
    
    if not query:
        return jsonify({'success': False, 'message': 'No query provided'}), 400
    
    # Check if global analyzer exists
    if global_analyzer is None:
        return jsonify({'success': False, 'message': 'Analyzer not initialized. Please restart the server.'}), 400
    
    if use_batch:
        return jsonify({
            'success': False,
            'batch_mode': True,
            'message': 'For large datasets (500+), use: python camera_analyzer_batch.py'
        })
    
    try:
        current_sess_id = session.get('current_analysis_session')
        
        if not current_sess_id:
            current_sess_id = session_manager.create_session(query)
            session['current_analysis_session'] = current_sess_id
        
        # Check if follow-up
        query_type = session_manager.analyze_query_type(query)
        
        if query_type['is_follow_up']:
            # Use context
            context = session_manager.get_context_for_query()
            previous_results = session_manager.get_previous_results()
            
            results = global_analyzer.process_contextual_query(query, context, previous_results)
        else:
            # Fresh analysis
            detailed_results = global_analyzer.analyze_all_images(query)
            matches_found = sum(1 for r in detailed_results if r.get('match', False))
            
            # Get query analysis for better context
            query_analysis = global_analyzer.analyze_user_query(query)
            
            final_report = global_analyzer.generate_final_report(query, query_analysis)
            
            results = {
                'total_images': len(detailed_results),
                'matches_found': matches_found,
                'unique_locations': len(set(r.get('location_name', '') for r in detailed_results)),
                'detailed_results': detailed_results,
                'final_answer': final_report
            }
        
        # Add to session
        session_manager.add_query(query, results)
        
        # Convert all Path objects to strings before returning
        results_clean = convert_paths_to_strings(results)
        
        return jsonify({
            'success': True,
            'results': results_clean,
            'is_contextual': results_clean.get('is_contextual', False)
        })
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Analysis error: {error_trace}")
        return jsonify({
            'success': False,
            'message': f'Analysis failed: {str(e)}'
        }), 500


@app.route('/get_sessions')
def get_sessions():
    """Get all sessions"""
    sessions = session_manager.get_all_sessions()
    # Convert all Path objects to strings
    sessions_clean = convert_paths_to_strings(sessions)
    return jsonify({'sessions': sessions_clean})


@app.route('/get_session/<session_id>')
def get_session(session_id):
    """Get session details"""
    sess = session_manager.load_session(session_id)
    if sess:
        # Convert all Path objects to strings before JSON serialization
        sess_clean = convert_paths_to_strings(sess)
        return jsonify({
            'success': True,
            'session': sess_clean
        })
    return jsonify({'success': False}), 404


@app.route('/delete_session/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Delete a session"""
    success = session_manager.delete_session(session_id)
    return jsonify({'success': success})


@app.route('/get_image/<path:filename>')
def get_image(filename):
    """
    Serve images via signed URL redirect (ZERO downloads!)
    Browser fetches directly from GCS
    """
    from urllib.parse import unquote
    from flask import redirect
    import os
    
    try:
        # Decode URL-encoded filename
        filename = unquote(filename)
        
        print(f"\n=== Image request: {filename} ===")
        
        # If using GCS, generate signed URL and redirect (NO download!)
        if gcs_manager and gcs_manager.use_gcs:
            print(f"  🔗 Generating signed URL from GCS (no server download!)...")
            
            # Try with different prefixes
            possible_prefixes = ['test/', 'a_test/', 'camera_images/', '']
            images_dir = os.getenv('IMAGES_DIR', 'test')
            
            # Put configured prefix first
            possible_prefixes.insert(0, f"{images_dir}/")
            possible_prefixes = list(dict.fromkeys(possible_prefixes))  # Remove duplicates
            
            for prefix in possible_prefixes:
                blob_name = f"{prefix}{filename}" if prefix else filename
                print(f"  🔍 Trying: {blob_name}")
                
                # Check if blob exists first
                try:
                    blob = gcs_manager.bucket.blob(blob_name)
                    if blob.exists():
                        # Try signed URL first
                        signed_url = gcs_manager.get_image_url(blob_name, expiration_minutes=60)
                        
                        if signed_url:
                            print(f"  ✅ Generated signed URL")
                            return redirect(signed_url)
                        else:
                            # Fallback: Public URL (if bucket is public or has uniform access)
                            print(f"  ⚠️  Signed URL failed, using public URL")
                            public_url = f"https://storage.googleapis.com/{gcs_manager.bucket_name}/{blob_name}"
                            return redirect(public_url)
                except Exception as e:
                    print(f"  ❌ Error checking blob: {e}")
                    continue
            
            print(f"  ⚠️  Image not found in GCS, trying local fallback...")
        
        # Fallback: Try local directories (only for local mode or development)
        possible_dirs = ['test', 'a_test', 'camera_images', 'images']
        
        if global_analyzer and hasattr(global_analyzer, 'images_dir'):
            possible_dirs.insert(0, str(global_analyzer.images_dir))
        
        for directory in possible_dirs:
            try:
                dir_path = Path(directory)
                if not dir_path.exists():
                    continue
                
                # Check if file exists
                file_path = dir_path / filename
                
                if file_path.exists() and file_path.is_file():
                    print(f"  ✅ FOUND locally at: {file_path}")
                    return send_file(
                        str(file_path),
                        mimetype='image/jpeg',
                        as_attachment=False
                    )
                    
            except Exception as e:
                print(f"  ❌ Error checking {directory}: {str(e)}")
                continue
        
        # If not found anywhere
        print(f"  ❌ Image not found in GCS or local storage")
        print(f"  Filename: {filename}")
        return "Image not found", 404
        
    except Exception as e:
        print(f"  ❌ FATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Error loading image: {str(e)}", 500


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})


# Initialize analyzer at module level (so it runs under gunicorn too!)
def initialize_app():
    """Initialize the application"""
    # Create necessary directories
    Path('templates').mkdir(exist_ok=True)
    Path('static').mkdir(exist_ok=True)
    Path('static/css').mkdir(exist_ok=True)
    Path('static/js').mkdir(exist_ok=True)
    Path('sessions').mkdir(exist_ok=True)
    Path('analysis_results').mkdir(exist_ok=True)
    
    # Initialize the analyzer
    print("\n🚀 Initializing Camera Analyzer...")
    init_success = init_global_analyzer()
    
    if not init_success:
        print("⚠️  WARNING: Analyzer initialization failed!")
        print("The server will start, but analysis features may not work.")
    else:
        print("✅ Analyzer initialized successfully!")
    
    return init_success

# Run initialization when module is imported (works with gunicorn!)
initialize_app()


if __name__ == '__main__':
    # Local development mode
    print("""
╔═══════════════════════════════════════════════════════════════╗
║          Flask Camera Analyzer - Development Mode             ║
║                                                                ║
║  🚀 Production-Ready CCTV Analysis Platform                   ║
╚═══════════════════════════════════════════════════════════════╝
""")
    
    print("""
╔═══════════════════════════════════════════════════════════════╗
║  🌐 Server Ready!                                             ║
║                                                                ║
║  Open your browser and go to:                                 ║
║  👉 http://localhost:5000                                     ║
║                                                                ║
║  Features:                                                     ║
║  ✅ Beautiful Bootstrap UI                                    ║
║  ✅ Session-based conversations                               ║
║  ✅ Real-time AI analysis                                     ║
║  ✅ Interactive maps                                          ║
║  ✅ Image display & metadata                                  ║
║  ✅ Production-ready performance                              ║
╚═══════════════════════════════════════════════════════════════╝
""")
    
    print("""
⚠️  Auto-reload: DISABLED (prevents SSE socket errors)
💡 Tip: Restart server manually after code changes (Ctrl+C then run again)
""")
    
    app.run(
        debug=True, 
        use_reloader=False,  # Disable auto-reload to prevent SSE socket errors
        host='0.0.0.0', 
        port=5000,
        threaded=True
    )

