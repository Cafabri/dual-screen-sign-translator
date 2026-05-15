const chalk = require('chalk');
const { ElevenLabsClient } = require('@elevenlabs/elevenlabs-js');

const client = new ElevenLabsClient({ apiKey: process.env.ELEVENLABS_API_KEY });

const synthesizeSpeech = async (text) => {
  console.log(chalk.blue(`[TTS] 🔊 Synthesizing: "${text}"`));

  const audioStream = await client.textToSpeech.convert(process.env.ELEVENLABS_VOICE_ID, {
    text,
    model_id: 'eleven_turbo_v2',
    output_format: 'mp3_44100_128',
  });

  const chunks = [];
  for await (const chunk of audioStream) {
    chunks.push(chunk);
  }

  const audioBase64 = Buffer.concat(chunks).toString('base64');
  console.log(chalk.blue.bold(`[TTS] ✅ Audio ready (${audioBase64.length} chars base64)`));

  return audioBase64;
};

module.exports = { synthesizeSpeech };
