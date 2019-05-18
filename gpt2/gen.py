#!/usr/bin/env python
import gpt_2_simple as gpt2
import sys

if len(sys.argv) > 1:
    prompt = sys.argv[1]
else:
    prompt = "prompt: So, what's new around here?"

print(prompt)
sys.exit(1)

sess = gpt2.start_tf_sess()
gpt2.load_gpt2(sess)

single_text = gpt2.generate(
        sess,
        return_as_list=True,
        temperature=0.75,
        include_prefix=False,
        truncate="<|endoftext|>",
        prefix="""ASCII Today - Fun with the Teletype Terminal"""
        )[0]

print(single_text)

