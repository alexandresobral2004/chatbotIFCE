import time
import uuid
import functools
import tiktoken
from typing import Callable, Any, Optional, AsyncGenerator

from ports.usage_log_port import UsageLogPort

# Cost per 1M tokens (USD)
COSTS = {
    "openai": {
        "gpt-4o-mini": {"input": 0.150, "output": 0.600},
        "text-embedding-3-small": {"input": 0.020, "output": 0.0},
        "gpt-5.6-luna": {"input": 0.20, "output": 1.20},
    },
    "deepseek": {
        "deepseek-chat": {"input": 0.140, "output": 0.280},
        "deepseek-v4-flash": {"input": 0.14, "output": 0.28},
    },
    "groq": {
        "llama3-8b-8192": {"input": 0.050, "output": 0.080},
        "mixtral-8x7b-32768": {"input": 0.240, "output": 0.240},
    }
}

def get_cost(provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
    provider_costs = COSTS.get(provider, {})
    model_costs = provider_costs.get(model, {"input": 0.0, "output": 0.0})
    
    input_cost = (input_tokens / 1_000_000) * model_costs["input"]
    output_cost = (output_tokens / 1_000_000) * model_costs["output"]
    return input_cost + output_cost

def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback to cl100k_base
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

def track_llm_usage(
    provider: str,
    endpoint_name: Optional[str] = None
):
    """
    Decorator to track LLM usage for adapter methods.
    Must be applied to async methods of a class that has a 'usage_adapter' attribute (a UsageLogPort).
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            self = args[0]
            usage_adapter: Optional[UsageLogPort] = getattr(self, "usage_adapter", None)
            # user_id is only for usage-log attribution — never forward it to the wrapped call.
            user_id = kwargs.pop("user_id", None)

            start_time = time.time()
            
            # Try to extract inputs for token counting
            input_text = ""
            if "messages" in kwargs:
                input_text = " ".join([m.get("content", "") for m in kwargs["messages"]])
            elif "text" in kwargs:
                input_text = kwargs["text"]
            elif "texts" in kwargs:
                input_text = " ".join(kwargs["texts"])
            elif len(args) > 1: # self, text/messages
                if isinstance(args[1], list):
                    if len(args[1]) > 0 and isinstance(args[1][0], dict):
                        input_text = " ".join([m.get("content", "") for m in args[1]])
                    elif len(args[1]) > 0 and isinstance(args[1][0], str):
                        input_text = " ".join(args[1])
                elif isinstance(args[1], str):
                    input_text = args[1]

            model = kwargs.get("model") or getattr(self, "model", "unknown")
            input_tokens = count_tokens(input_text, model)
            
            is_stream = kwargs.get("stream", False)

            if is_stream:
                # Return an async generator so callers can `async for` over it
                async def stream_wrapper():
                    output_text = ""
                    gen = func(*args, **kwargs)
                    async for chunk in gen:
                        if chunk:
                            output_text += chunk
                        yield chunk
                    
                    if usage_adapter:
                        latency_ms = int((time.time() - start_time) * 1000)
                        output_tokens = count_tokens(output_text, model)
                        total_cost = get_cost(provider, model, input_tokens, output_tokens)
                        
                        await usage_adapter.log_usage(
                            provider=provider,
                            model=model,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            total_cost=total_cost,
                            latency_ms=latency_ms,
                            user_id=user_id,
                            endpoint=endpoint_name or func.__name__
                        )
                return stream_wrapper()
            else:
                # Return a coroutine for standard `await` callers
                async def non_stream_wrapper():
                    result = await func(*args, **kwargs)
                    latency_ms = int((time.time() - start_time) * 1000)
                    
                    output_text = ""
                    if isinstance(result, str):
                        output_text = result
                    elif isinstance(result, dict) and "content" in result:
                        output_text = result["content"]
                    elif hasattr(result, "__iter__") and not isinstance(result, dict):
                        output_text = str(result) # fallback for embeddings

                    # Assume output tokens for embeddings is 0
                    output_tokens = 0
                    if "embed" not in func.__name__:
                        output_tokens = count_tokens(output_text, model)
                    
                    total_cost = get_cost(provider, model, input_tokens, output_tokens)
                    
                    if usage_adapter:
                        await usage_adapter.log_usage(
                            provider=provider,
                            model=model,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            total_cost=total_cost,
                            latency_ms=latency_ms,
                            user_id=user_id,
                            endpoint=endpoint_name or func.__name__
                        )

                    return result

                return non_stream_wrapper()

        return wrapper
    return decorator
