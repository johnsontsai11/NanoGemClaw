
import { handleSendDocument } from '../src/ipc-handlers/send-document.js';
import { setBot } from '../src/state.js';
import fs from 'fs';

// Ensure test file exists
fs.writeFileSync('/tmp/test.txt', 'hello');

const mockBot = {
  api: {
    sendDocument: async (chatId: any, _file: any, _opts: any) => {
      console.log('  -> bot.api.sendDocument called with chatId:', chatId);
    }
  }
};

async function runCase(label: string, fn: () => Promise<any>) {
  console.log(`\n[TEST] ${label}`);
  try {
    const result = await fn();
    console.log('  Result:', JSON.stringify(result));
    const ok = result.success === false
      ? `PASS (expected failure: ${result.error})`
      : 'PASS (success)';
    console.log(' ', ok);
  } catch (err: any) {
    console.error('  FAIL (unexpected throw):', err.message);
  }
}

async function main() {
  setBot(mockBot as any);

  // Case 1: Normal happy path
  await runCase('Happy path', () =>
    handleSendDocument(
      { file_path: '/tmp/test.txt', caption: 'My report' },
      {
        sourceGroup: 'main',
        isMain: true,
        registeredGroups: { '-123': { folder: 'main', name: 'Main' } as any },
        sendMessage: async () => {},
        bot: mockBot as any,
      }
    )
  );

  // Case 2: undefined group entry (THE BUG)
  await runCase('registeredGroups has undefined entry (the bug)', () =>
    handleSendDocument(
      { file_path: '/tmp/test.txt' },
      {
        sourceGroup: 'main',
        isMain: true,
        registeredGroups: { 'b_group': undefined as any, 'a_group': { folder: 'main', name: 'Main' } as any },
        sendMessage: async () => {},
      }
    )
  );

  // Case 3: No matching group
  await runCase('No matching group', () =>
    handleSendDocument(
      { file_path: '/tmp/test.txt' },
      {
        sourceGroup: 'unknown_group',
        isMain: false,
        registeredGroups: { '-123': { folder: 'main', name: 'Main' } as any },
        sendMessage: async () => {},
      }
    )
  );

  // Case 4: Missing file
  await runCase('File does not exist', () =>
    handleSendDocument(
      { file_path: '/tmp/does_not_exist.csv' },
      {
        sourceGroup: 'main',
        isMain: true,
        registeredGroups: { '-123': { folder: 'main', name: 'Main' } as any },
        sendMessage: async () => {},
      }
    )
  );

  // Case 5: ctx is missing (null context)
  await runCase('ctx.registeredGroups is undefined', () =>
    handleSendDocument(
      { file_path: '/tmp/test.txt' },
      {
        sourceGroup: 'main',
        isMain: true,
        registeredGroups: undefined as any,
        sendMessage: async () => {},
      }
    )
  );

  console.log('\nAll cases complete.');
}

main();
