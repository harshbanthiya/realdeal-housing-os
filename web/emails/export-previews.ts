import { render } from '@react-email/render';
import EmailA from './drip-1-variant-a';
import EmailB from './drip-1-variant-b';
import { writeFileSync, mkdirSync } from 'fs';
(async () => {
  mkdirSync('/tmp/rdh-email-previews', { recursive: true });
  writeFileSync('/tmp/rdh-email-previews/variant-a.html', await render(EmailA({ firstName: 'Rajkumar' })));
  writeFileSync('/tmp/rdh-email-previews/variant-b.html', await render(EmailB({ firstName: 'Rajkumar' })));
  console.log('Saved to /tmp/rdh-email-previews/');
})();
