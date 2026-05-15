const chalk = require('chalk');
const Groq = require('groq-sdk');

const groq = new Groq({ apiKey: process.env.GROQ_API_KEY });

const analyzeSentiment = async (text) => {
  console.log(chalk.yellow(`[Sentiment] 🔍 Analyzing: "${text}"`));

  const completion = await groq.chat.completions.create({
    model: 'llama-3.1-8b-instant',
    messages: [
      {
        role: 'system',
        content:
          'You are a sentiment classifier. Classify the emotional tone of the sentence as ' +
          'positive, neutral, or negative. Be decisive — lean positive for warm, happy, or grateful ' +
          'messages; lean negative for unhappy, frustrated, sad, or rejecting messages; use neutral ' +
          'only for purely factual or ambiguous statements.\n\n' +
          'Examples:\n' +
          '"Yes that sounds great, thank you!" → positive\n' +
          '"I love that idea!" → positive\n' +
          '"Sure, okay." → neutral\n' +
          '"I need a moment to think." → neutral\n' +
          '"No, I don\'t like that." → negative\n' +
          '"I\'m really frustrated right now." → negative\n\n' +
          'Reply with ONLY one word: positive, neutral, or negative.',
      },
      {
        role: 'user',
        content: text,
      },
    ],
    temperature: 0.2,
    max_tokens: 5,
  });

  const raw = completion.choices[0].message.content.trim().toLowerCase();
  const sentiment = ['positive', 'negative', 'neutral'].includes(raw) ? raw : 'neutral';

  console.log(chalk.yellow.bold(`[Sentiment] ✅ Result: `) + chalk.white(sentiment));
  return sentiment;
};

module.exports = { analyzeSentiment };
