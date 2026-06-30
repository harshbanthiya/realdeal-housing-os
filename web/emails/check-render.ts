import { render } from '@react-email/render';
import EmailA from './drip-1-variant-a';
import EmailB from './drip-1-variant-b';
(async () => {
  const ha = await render(EmailA({ firstName: 'Rajkumar' }));
  const hb = await render(EmailB({ firstName: 'Rajkumar' }));
  console.log('Variant A:', ha.length, 'chars | CTA:', ha.includes('Send me the project brief'));
  console.log('Variant B:', hb.length, 'chars | CTA:', hb.includes('Request early access'));
  console.log('A teal:', ha.includes('1f3d4d'), '| amber:', ha.includes('b6862c'));
  console.log('B dark hero:', hb.includes('DLF enters Mumbai'), '| disclaimer:', hb.includes('not financial advice'));
})();
