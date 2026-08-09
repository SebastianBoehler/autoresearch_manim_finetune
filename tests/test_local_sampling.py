from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from mac_pipeline.local_sampling import build_runtime_options
from mac_pipeline.types import GenerationConfig


class LocalSamplingTests(unittest.TestCase):
    def test_build_runtime_options_passes_repetition_penalties(self) -> None:
        make_sampler = Mock(return_value="sampler")
        make_logits_processors = Mock(return_value=["processor"])
        tokenizer = SimpleNamespace(
            eos_token_ids=[2],
            bos_token=None,
            encode=lambda text, add_special_tokens=True: [10],
        )
        generation = GenerationConfig(
            temperature=0.15,
            top_p=0.9,
            top_k=32,
            repetition_penalty=1.08,
            repetition_context_size=96,
            presence_penalty=0.02,
            presence_context_size=80,
            frequency_penalty=0.04,
            frequency_context_size=72,
        )

        with patch(
            "mac_pipeline.local_sampling._import_sampling_runtime",
            return_value=("mx", "stream_generate", make_sampler, make_logits_processors),
        ):
            sampler, processors, mx, stream_generate = build_runtime_options(
                tokenizer,
                generation,
            )

        self.assertEqual(sampler, "sampler")
        self.assertEqual(processors, ["processor"])
        self.assertEqual(mx, "mx")
        self.assertEqual(stream_generate, "stream_generate")
        make_sampler.assert_called_once()
        make_logits_processors.assert_called_once_with(
            logit_bias=None,
            repetition_penalty=1.08,
            repetition_context_size=96,
            presence_penalty=0.02,
            presence_context_size=80,
            frequency_penalty=0.04,
            frequency_context_size=72,
        )

    def test_build_runtime_options_suppresses_single_token_texts(self) -> None:
        make_sampler = Mock(return_value="sampler")
        make_logits_processors = Mock(return_value=["processor"])
        tokenizer = SimpleNamespace(
            eos_token_ids=[2],
            bos_token=None,
            encode=lambda text, add_special_tokens=True: {
                "opacity": [20570],
                " opacity": [18655],
                "\n": [10],
            }[text],
        )
        generation = GenerationConfig(suppressed_token_texts=["opacity", " opacity"])

        with patch(
            "mac_pipeline.local_sampling._import_sampling_runtime",
            return_value=("mx", "stream_generate", make_sampler, make_logits_processors),
        ):
            build_runtime_options(tokenizer, generation)

        self.assertEqual(
            make_logits_processors.call_args.kwargs["logit_bias"],
            {20570: -100.0, 18655: -100.0},
        )

    def test_build_runtime_options_rejects_multi_token_suppression(self) -> None:
        make_sampler = Mock(return_value="sampler")
        make_logits_processors = Mock(return_value=[])
        tokenizer = SimpleNamespace(
            eos_token_ids=[2],
            bos_token=None,
            encode=lambda text, add_special_tokens=True: [1, 2],
        )
        generation = GenerationConfig(suppressed_token_texts=["tick_frequency="])

        with patch(
            "mac_pipeline.local_sampling._import_sampling_runtime",
            return_value=("mx", "stream_generate", make_sampler, make_logits_processors),
        ):
            with self.assertRaises(ValueError):
                build_runtime_options(tokenizer, generation)


if __name__ == "__main__":
    unittest.main()
