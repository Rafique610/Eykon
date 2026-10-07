import litert_lm
from src.assistant.llm import resolve_model_path

def test_vision():
    model_path = str(resolve_model_path())
    print(f"Loading engine from {model_path}...")
    
    from PIL import Image
    img = Image.new('RGB', (224, 224), color='red')
    img_path = 'data/dummy_test_image.jpg'
    img.save(img_path)
    
    try:
        # User provided snippet format
        engine = litert_lm.Engine(
            model_path=model_path,
            backend=litert_lm.Backend.CPU(),
            vision_backend=litert_lm.Backend.CPU()
        )
        conv = engine.create_conversation()
        
        print("Sending multimodal message...")
        user_message = {
            "role": "user",
            "content": [
                {"type": "image", "path": img_path},
                {"type": "text", "text": "Describe this image."},
            ],
        }
        res = conv.send_message(user_message)
        print("SUCCESS! Response:")
        print(res)
        
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    test_vision()
