import {countTokens} from '@anthropic-ai/tokenizer';

let data = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => data += chunk);
process.stdin.on('end', () => {
    const tokens = countTokens(data);
    process.stdout.write(String(tokens));
});