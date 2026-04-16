import os
import sys

def patch_mineru():
    # Try to find the mineru_vl_utils package in the current environment
    try:
        import mineru_vl_utils
        base_dir = os.path.dirname(mineru_vl_utils.__file__)
        target_file = os.path.join(base_dir, "vlm_client", "transformers_client.py")
        
        if not os.path.exists(target_file):
            print(f"Target file not found at {target_file}")
            return False
            
        with open(target_file, "r", encoding="utf-8") as f:
            content = f.read()
            
        old_code = "self.model_max_length = model.config.max_position_embeddings"
        new_code = 'self.model_max_length = getattr(model.config, "max_position_embeddings", getattr(getattr(model.config, "text_config", model.config), "max_position_embeddings", 32768))'
        
        if new_code in content:
            print("✅ MinerU VL Utils is already patched.")
            return True
            
        if old_code in content:
            content = content.replace(old_code, new_code)
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(content)
            print("✅ Successfully patched MinerU VL Utils for Transformers compatibility.")
            return True
        else:
            print("⚠️ Could not find the target code to patch. The package might have been updated or already patched manually.")
            return True # Not necessarily an error if it doesn't match old_code but also doesn't match new_code (e.g. they fixed it upstream)
            
    except ImportError:
        print("❌ mineru_vl_utils is not installed. Please install dependencies first.")
        return False
    except Exception as e:
        print(f"❌ Error patching mineru: {e}")
        return False

if __name__ == "__main__":
    print("Running MinerU compatibility patch...")
    success = patch_mineru()
    sys.exit(0 if success else 1)
