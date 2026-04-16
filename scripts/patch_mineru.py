import os
import sys

def patch_mineru_vl_utils():
    """Patch mineru_vl_utils for transformers compatibility."""
    try:
        import mineru_vl_utils
        base_dir = os.path.dirname(mineru_vl_utils.__file__)
        target_file = os.path.join(base_dir, "vlm_client", "transformers_client.py")
        
        if not os.path.exists(target_file):
            print(f"⚠️ Target file not found at {target_file}")
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
            print("⚠️ Could not find the target code to patch in MinerU VL Utils. The package might have been updated or already patched manually.")
            return True
            
    except ImportError:
        print("❌ mineru_vl_utils is not installed. Please install dependencies first.")
        return False
    except Exception as e:
        print(f"❌ Error patching mineru_vl_utils: {e}")
        return False

def patch_mineru_layout():
    """Patch mineru layout model for transformers compatibility."""
    try:
        import mineru
        base_dir = os.path.dirname(mineru.__file__)
        target_file = os.path.join(base_dir, "model", "layout", "pp_doclayoutv2.py")
        
        if not os.path.exists(target_file):
            print(f"⚠️ Target file not found at {target_file}")
            return False
            
        with open(target_file, "r", encoding="utf-8") as f:
            content = f.read()
            
        old_code = """        super().__init__(
            backbone_config=backbone_config,
            class_thresholds=class_thresholds or list(DEFAULT_CLASS_THRESHOLDS),
            class_order=class_order or list(DEFAULT_CLASS_ORDER),
            **kwargs,
        )
        self.class_thresholds = list(class_thresholds or DEFAULT_CLASS_THRESHOLDS)
        self.class_order = list(class_order or DEFAULT_CLASS_ORDER)
        self.reading_order_config = reading_order"""
        
        new_code = """        self.class_thresholds = list(class_thresholds or DEFAULT_CLASS_THRESHOLDS)
        self.class_order = list(class_order or DEFAULT_CLASS_ORDER)
        self.reading_order_config = reading_order

        super().__init__(
            backbone_config=backbone_config,
            class_thresholds=class_thresholds or list(DEFAULT_CLASS_THRESHOLDS),
            class_order=class_order or list(DEFAULT_CLASS_ORDER),
            **kwargs,
        )"""
        
        if new_code in content:
            print("✅ MinerU Layout is already patched.")
            return True
            
        if old_code in content:
            content = content.replace(old_code, new_code)
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(content)
            print("✅ Successfully patched MinerU Layout for Transformers compatibility.")
            return True
        else:
            print("⚠️ Could not find the target code to patch in MinerU Layout. The package might have been updated or already patched manually.")
            return True
            
    except ImportError:
        print("❌ mineru is not installed. Please install dependencies first.")
        return False
    except Exception as e:
        print(f"❌ Error patching mineru layout: {e}")
        return False

if __name__ == "__main__":
    print("Running MinerU compatibility patches...")
    success_vl = patch_mineru_vl_utils()
    success_layout = patch_mineru_layout()
    sys.exit(0 if (success_vl and success_layout) else 1)
