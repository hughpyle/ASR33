# AI and a Teletype

I took the (very impressive) [GPT-2 345M text-generating language model](https://openai.com/blog/better-language-models/) from OpenAI,
and fine-tuned its training with the [Teletype technical documentation](https://github.com/hughpyle/ASR33/tree/master/doc) from the late 1960s - early 1970s.

Here's the [training text](https://raw.githubusercontent.com/hughpyle/ASR33/master/gpt2/training.txt), after OCR and cleanup.
It's about a megabyte, with quite a lot of repetition, and several distinctive styles: it's very dry reading, and mostly consists of
series of numbered paragraphs.

I ran the training using [gpt-2-simple](https://github.com/minimaxir/gpt-2-simple), with 
a [Google Colaboratory notebook](https://colab.research.google.com/drive/1VLG8e7YSEwypxU-noRNhsv5dW4NfTGce)
that make the whole process really easy (and free!).  A training run of 10000 iterations took about 4 hours.


Once the model was finetuned, then to run the text generation, first a tiny [Python command-line](https://github.com/hughpyle/ASR33/blob/master/gpt2/gen.py).
It works well enough, and produces text that's some strange combination of your prompt and the tech manuals and
whatever else the model wants to talk about (randomly).

```
New Year's Eve - In honor of our new year we did a little shopping. We picked up a used dialer from the hardware section for $100, and a used dialer and polar relay from the fabricators' section for $80.
New Tool - The Polar Relay washers werehers werehers werehers werehers were also werehers were for the H-bridge and the T-lever when used with the T-apparatus. 
```

Now, to actually run this from the Teletype,
* I spun up an Amazon "Deep Learning" AMI on one of their cheapest GPU servers (`g3s.xlarge`),
* There, ran a tiny [Python web server](https://github.com/hughpyle/ASR33/blob/master/gpt2/web.py) that takes a prompt and produces some text in response,
* Hooked that up to the [twitchbot](https://github.com/hughpyle/ASR33/blob/master/bin/twitchbot),
* and then we [chatted away on Twitch.tv](https://www.twitch.tv/videos/426617997) and watched what happened.

It's quite a trip.
[![teletype with generated text](https://pbs.twimg.com/media/D64QvkcWwAE2lDW.jpg)](https://twitter.com/33asr/status/1129858972419330049) 