const chalk = require('chalk');
const Groq = require('groq-sdk');

const groq = new Groq({ apiKey: process.env.GROQ_API_KEY });

const enrichGlossToNaturalEnglish = async (rawGloss) => {
  console.log(chalk.yellow(`[NLP] 🤖 Enriching gloss with Groq: "${rawGloss}"`));

  const completion = await groq.chat.completions.create({
    model: 'llama-3.1-8b-instant',
    messages: [
      {
        role: 'system',
        content:
          'You are a real-time ASL interpreter in a live conversation between a deaf person and a hearing person.\n\n' +
          'The deaf person signs in ASL gloss: uppercase English words representing signs, with no grammatical particles. ' +
          'Convert each gloss into the natural spoken English phrase the deaf person intends to communicate at that moment.\n\n' +
          'RULES — follow all of them without exception:\n' +
          '- This is a live conversation, not a vocabulary exercise. NEVER define, describe, or explain what a word means.\n' +
          '- A single noun or verb means the person is requesting, mentioning, or reacting — not asking for a definition.\n' +
          '- Keep output short and natural. One sentence maximum.\n' +
          '- Reply with ONLY the English phrase. No quotes, no labels, no extra text.\n\n' +
          'Examples:\n' +
          'APPLE → Apple, please.\n' +
          'WATER → Could I have some water?\n' +
          'HELP → I need help!\n' +
          'THANK YOU → Thank you!\n' +
          'MORE WATER → More water, please.\n' +
          'HELLO → Hello!\n' +
          'NO → No, thank you.\n' +
          'YES → Yes!\n' +
          'PLEASE HELP → Please help me.',
      },
      {
        role: 'user',
        content: rawGloss,
      },
    ],
    temperature: 0.4,
    max_tokens: 120,
  });

  const enrichedText = completion.choices[0].message.content.trim();
  console.log(chalk.yellow.bold(`[NLP] ✅ Enriched: `) + chalk.white(`"${enrichedText}"`));

  return enrichedText;
};

module.exports = { enrichGlossToNaturalEnglish };
