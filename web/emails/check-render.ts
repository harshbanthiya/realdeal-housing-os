import { render } from '@react-email/render';
import EmailA from './drip-1-variant-a';
import EmailB from './drip-1-variant-b';
(async () => {
  const ha = await render(EmailA({ firstName: 'Rajkumar' }));
  const hb = await render(EmailB({ firstName: 'Rajkumar' }));
  console.log('Variant A:', ha.length, 'chars | sold-out hook:', ha.includes('7 days'), '| amber:', ha.includes('b6862c'), '| 4BHK:', ha.includes('4BHK'));
  console.log('Variant B:', hb.length, 'chars | sold-out hook:', hb.includes('7 days'), '| amber:', hb.includes('b6862c'), '| EOI:', hb.includes('EOI'));
})();
