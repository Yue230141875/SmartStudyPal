import sys
import os
import importlib
import threading
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))

results = {}


def check_dependency(module_name, import_name=None):
    if import_name is None:
        import_name = module_name
    try:
        importlib.import_module(import_name)
        return True
    except ImportError:
        return False


def check_dependencies():
    print("\n[1/5] 检查Python依赖...")
    deps = [
        ("cv2", "opencv-python"),
        ("dlib", "dlib"),
        ("mediapipe", "mediapipe"),
        ("whisper", "openai-whisper"),
        ("librosa", "librosa"),
        ("pyttsx3", "pyttsx3"),
        ("webrtcvad", "webrtcvad-wheels"),
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("numpy", "numpy"),
    ]
    dep_results = {}
    pass_count = 0
    for import_name, pip_name in deps:
        ok = check_dependency(import_name)
        dep_results[pip_name] = ok
        status = "OK" if ok else "FAIL"
        if ok:
            pass_count += 1
        else:
            print(f"  [FAIL] {pip_name} — 安装命令: pip install {pip_name}")
        print(f"  [{status}] {pip_name}")
    results["dependencies"] = dep_results
    all_pass = pass_count == len(deps)
    results["dep_status"] = "通过" if all_pass else f"部分通过({pass_count}/{len(deps)})"
    return all_pass


def check_model_file():
    print("\n[2/5] 检查模型文件...")
    model_path = os.path.join(PROJECT_ROOT, "backend", "models", "shape_predictor_68_face_landmarks.dat")
    exists = os.path.exists(model_path)
    if exists:
        size_mb = os.path.getsize(model_path) / (1024 * 1024)
        print(f"  [OK] Dlib模型文件存在 ({size_mb:.1f}MB)")
        results["model_status"] = "通过"
    else:
        print(f"  [FAIL] Dlib模型文件不存在")
        print(f"  下载命令:")
        print(f"    wget http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2")
        print(f"    bzip2 -d shape_predictor_68_face_landmarks.dat.bz2")
        print(f"    移动到: {model_path}")
        results["model_status"] = "失败"
    return exists


def test_module(module_path, func_name, display_name):
    try:
        module = importlib.import_module(module_path)
        if hasattr(module, func_name):
            getattr(module, func_name)()
            return True
        else:
            print(f"  [SKIP] {display_name}: 未找到 {func_name}() 函数")
            return None
    except Exception as e:
        print(f"  [FAIL] {display_name}: {e}")
        return False


def check_modules():
    print("\n[3/5] 测试功能模块...")
    modules = [
        ("modules.vision.image_preprocessor", "test", "图像预处理"),
        ("modules.vision.face_detector", "test", "人脸检测"),
        ("modules.vision.focus_scorer", "test", "专注度评分"),
        ("modules.vision.pose_estimator", "test", "姿态估计"),
        ("modules.voice.vad_detector", "test", "VAD静音检测"),
        ("modules.voice.asr_whisper", "test", "Whisper语音识别"),
        ("modules.voice.tts_engine", "test", "TTS语音合成"),
        ("modules.voice.emotion_classifier", "test", "情绪分类"),
        ("modules.voice.wake_word", "test", "唤醒词检测"),
        ("modules.fusion_engine", "test", "多模态融合引擎"),
    ]
    module_results = {}
    pass_count = 0
    for module_path, func_name, display_name in modules:
        result = test_module(module_path, func_name, display_name)
        module_results[display_name] = result
        if result is True:
            pass_count += 1
            print(f"  [OK] {display_name}")
        elif result is False:
            print(f"  [FAIL] {display_name}")
        else:
            print(f"  [SKIP] {display_name}")
    results["modules"] = module_results
    tested = sum(1 for v in module_results.values() if v is not None)
    results["module_status"] = f"通过({pass_count}/{tested})" if pass_count == tested else f"部分通过({pass_count}/{tested})"
    return pass_count == tested


def check_fastapi():
    print("\n[4/5] 测试FastAPI服务...")
    try:
        import uvicorn
        from main import app
        import urllib.request

        server_started = threading.Event()

        def run_server():
            config = uvicorn.Config(app, host="127.0.0.1", port=8765, log_level="error")
            server = uvicorn.Server(config)
            threading.Thread(target=server.run, daemon=True).start()
            time.sleep(2)
            server_started.set()
            time.sleep(3)

        t = threading.Thread(target=run_server, daemon=True)
        t.start()
        server_started.wait(timeout=5)

        try:
            resp = urllib.request.urlopen("http://127.0.0.1:8765/", timeout=3)
            if resp.status == 200:
                print("  [OK] FastAPI服务启动成功，GET / 返回200")
                results["fastapi_status"] = "通过"
                return True
        except Exception:
            pass

        print("  [FAIL] FastAPI服务启动失败")
        results["fastapi_status"] = "失败"
        return False
    except Exception as e:
        print(f"  [FAIL] FastAPI服务测试异常: {e}")
        results["fastapi_status"] = "失败"
        return False


def check_frontend():
    print("\n[5/5] 检查前端项目...")
    pkg_path = os.path.join(PROJECT_ROOT, "frontend", "package.json")
    exists = os.path.exists(pkg_path)
    if exists:
        print(f"  [OK] frontend/package.json 存在")
        results["frontend_status"] = "通过"
    else:
        print(f"  [FAIL] frontend/package.json 不存在")
        results["frontend_status"] = "失败"
    return exists


def print_report():
    print("\n" + "=" * 48)
    print("Week7 技术可行性验证报告")
    print("=" * 48)

    print(f"\n1. Python依赖检查: {results.get('dep_status', '未知')}")
    for pip_name, ok in results.get("dependencies", {}).items():
        status = "OK" if ok else "FAIL"
        print(f"   - {pip_name}: [{status}]")

    print(f"\n2. 模型文件检查: {results.get('model_status', '未知')}")

    print(f"\n3. 功能模块测试: {results.get('module_status', '未知')}")
    for name, ok in results.get("modules", {}).items():
        if ok is True:
            status = "OK"
        elif ok is False:
            status = "FAIL"
        else:
            status = "SKIP"
        print(f"   - {name}: [{status}]")

    print(f"\n4. FastAPI服务: {results.get('fastapi_status', '未知')}")
    print(f"\n5. 前端项目: {results.get('frontend_status', '未知')}")

    all_checks = [
        results.get("dep_status", "") == "通过",
        results.get("model_status", "") == "通过",
        "通过" in results.get("module_status", ""),
        results.get("fastapi_status", "") == "通过",
        results.get("frontend_status", "") == "通过",
    ]
    pass_count = sum(all_checks)
    if pass_count == 5:
        conclusion = "全部通过"
    elif pass_count >= 3:
        conclusion = "部分通过"
    else:
        conclusion = "未通过"

    print(f"\n{'=' * 48}")
    print(f"总体结论: {conclusion}")
    print(f"{'=' * 48}")


if __name__ == "__main__":
    print("=" * 48)
    print("Week7 技术可行性验证")
    print("=" * 48)
    check_dependencies()
    check_model_file()
    check_modules()
    check_fastapi()
    check_frontend()
    print_report()
