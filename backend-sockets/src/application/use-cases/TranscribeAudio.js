const chalk = require('chalk');
const fs    = require('fs');
const path  = require('path');
const os    = require('os');
const Groq  = require('groq-sdk');

const groq = new Groq({ apiKey: process.env.GROQ_API_KEY });

const transcribeAudio = async (audioBuffer, mimeType = 'audio/webm') => {
  console.log(chalk.magenta(`[UseCase] 🎙️ Transcribing audio (${audioBuffer.byteLength} bytes, ${mimeType})...`));

  const ext      = mimeType.includes('mp4') || mimeType.includes('m4a') ? 'mp4' : 'webm';
  const tempPath = path.join(os.tmpdir(), `dualsign_${Date.now()}.${ext}`);

  try {
    fs.writeFileSync(tempPath, Buffer.from(audioBuffer));

    const result = await groq.audio.transcriptions.create({
      file:            fs.createReadStream(tempPath),
      model:           'whisper-large-v3-turbo',
      language:        'en',
      response_format: 'verbose_json',
    });

    const text = (result?.text ?? result ?? '').toString().trim();

    if (!text) {
      return { status: 'error', message: 'No speech detected.' };
    }

    console.log(chalk.magenta.bold(`[UseCase] ✅ Transcript: `) + chalk.white(`"${text}"`));
    return { status: 'success', text };
  } catch (err) {
    console.log(chalk.red.bold(`[UseCase] ❌ Transcription error:`), err.message);
    return { status: 'error', message: 'Transcription failed. Check your Groq API key.' };
  } finally {
    try { fs.unlinkSync(tempPath); } catch (_) {}
  }
};

module.exports = { transcribeAudio };
