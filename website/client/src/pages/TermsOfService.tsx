/* Cinematic Noir Tech - Terms of Service Page
 * Legal document page with clean typography
 */

import Navbar from "@/components/Navbar";
import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";
import { useLocation } from "wouter";

export default function TermsOfService() {
  const [, setLocation] = useLocation();

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Navbar />
      
      <div className="container max-w-4xl py-16 px-6">
        <Button
          variant="outline"
          className="mb-8 border-border/50 hover:border-primary/50"
          onClick={() => setLocation("/")}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Home
        </Button>

        <article className="prose prose-invert max-w-none">
          <h1 className="text-4xl font-display font-bold mb-4 text-foreground">Terms of Service</h1>
          <p className="text-muted-foreground mb-8">Last Updated: February 22, 2026</p>

          <section className="mb-8">
            <h2 className="text-2xl font-display font-semibold mt-8 mb-4 text-foreground">1. Acceptance of Terms</h2>
            <p className="text-foreground/90 leading-relaxed">
              By accessing or using Luna2077 ("Luna", "the Service", "our platform"), you agree to be bound by these Terms of Service ("Terms"). If you do not agree to these Terms, please do not use our Service. These Terms constitute a legally binding agreement between you and Luna2077.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-display font-semibold mt-8 mb-4 text-foreground">2. Description of Service</h2>
            <p className="text-foreground/90 leading-relaxed mb-4">
              Luna2077 is an AI-powered interactive storytelling platform that provides:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-foreground/90">
              <li>AI character interactions with memory retention capabilities</li>
              <li>Dynamic visual generation based on story progression</li>
              <li>Personalized narrative experiences</li>
              <li>Subscription-based access to premium features</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-display font-semibold mt-8 mb-4 text-foreground">3. Fictional Content Disclaimer</h2>
            <p className="text-foreground/90 leading-relaxed mb-4">
              <strong>All AI characters, personalities, and narratives on Luna2077 are entirely fictional.</strong> Characters do not represent real people, and any resemblance to actual persons, living or dead, is purely coincidental.
            </p>
            <p className="text-foreground/90 leading-relaxed mb-4">
              AI-generated responses are created by machine learning models and do not reflect the opinions, beliefs, or advice of Luna2077 or its operators. Users should not rely on AI characters for:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-foreground/90">
              <li>Medical, legal, financial, or professional advice</li>
              <li>Emergency assistance or crisis intervention</li>
              <li>Factual information or news</li>
              <li>Therapeutic or mental health services</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-display font-semibold mt-8 mb-4 text-foreground">4. User Eligibility</h2>
            <p className="text-foreground/90 leading-relaxed mb-4">
              You must be at least 18 years old to use Luna2077. By using the Service, you represent and warrant that you meet this age requirement and have the legal capacity to enter into these Terms.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-display font-semibold mt-8 mb-4 text-foreground">5. Subscription and Billing</h2>
            
            <h3 className="text-xl font-semibold mt-6 mb-3 text-foreground">5.1 Subscription Plans</h3>
            <p className="text-foreground/90 leading-relaxed mb-4">
              Luna2077 offers the following subscription tiers:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-foreground/90">
              <li><strong>Explorer (Free):</strong> Limited daily messages and basic features</li>
              <li><strong>Neural Link:</strong> Unlimited messages, all characters, and advanced features (billed monthly or yearly)</li>
              <li><strong>Corporate:</strong> Custom solutions with API access and dedicated support</li>
            </ul>

            <h3 className="text-xl font-semibold mt-6 mb-3 text-foreground">5.2 Payment Processing</h3>
            <p className="text-foreground/90 leading-relaxed mb-4">
              All payments are processed securely through Stripe. By subscribing, you authorize us to charge your payment method on a recurring basis according to your selected billing cycle (monthly or yearly).
            </p>

            <h3 className="text-xl font-semibold mt-6 mb-3 text-foreground">5.3 Automatic Renewal</h3>
            <p className="text-foreground/90 leading-relaxed mb-4">
              Subscriptions automatically renew at the end of each billing period unless you cancel before the renewal date. You will be charged the then-current subscription rate.
            </p>

            <h3 className="text-xl font-semibold mt-6 mb-3 text-foreground">5.4 Price Changes</h3>
            <p className="text-foreground/90 leading-relaxed mb-4">
              We reserve the right to modify subscription prices. Price changes will be communicated at least 30 days in advance and will apply to subsequent billing cycles.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-display font-semibold mt-8 mb-4 text-foreground">6. Cancellation and Refunds</h2>
            
            <h3 className="text-xl font-semibold mt-6 mb-3 text-foreground">6.1 Cancellation</h3>
            <p className="text-foreground/90 leading-relaxed mb-4">
              You may cancel your subscription at any time through your account settings. Cancellation will take effect at the end of your current billing period, and you will retain access until that date.
            </p>

            <h3 className="text-xl font-semibold mt-6 mb-3 text-foreground">6.2 No Refunds Policy</h3>
            <p className="text-foreground/90 leading-relaxed mb-4">
              <strong>Due to the digital nature of our services, all subscription fees are non-refundable.</strong> We do not provide refunds or credits for:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-foreground/90">
              <li>Partial billing periods</li>
              <li>Unused subscription time</li>
              <li>Dissatisfaction with the service</li>
              <li>Account termination or suspension</li>
            </ul>
            <p className="text-foreground/90 leading-relaxed mt-4">
              We encourage you to use the free Explorer tier to evaluate the service before subscribing to a paid plan.
            </p>

            <h3 className="text-xl font-semibold mt-6 mb-3 text-foreground">6.3 Exceptions</h3>
            <p className="text-foreground/90 leading-relaxed mb-4">
              Refunds may be considered on a case-by-case basis for:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-foreground/90">
              <li>Duplicate charges due to technical errors</li>
              <li>Unauthorized charges (subject to verification)</li>
              <li>Service outages exceeding 48 consecutive hours</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-display font-semibold mt-8 mb-4 text-foreground">7. User-Generated Content</h2>
            
            <h3 className="text-xl font-semibold mt-6 mb-3 text-foreground">7.1 Your Content</h3>
            <p className="text-foreground/90 leading-relaxed mb-4">
              You retain ownership of all content you create through interactions with Luna2077, including:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-foreground/90">
              <li>Chat messages and conversation history</li>
              <li>Story choices and narrative decisions</li>
              <li>Custom character preferences</li>
            </ul>

            <h3 className="text-xl font-semibold mt-6 mb-3 text-foreground">7.2 License to Luna2077</h3>
            <p className="text-foreground/90 leading-relaxed mb-4">
              By using the Service, you grant Luna2077 a limited, non-exclusive license to:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-foreground/90">
              <li>Store and process your content to provide the Service</li>
              <li>Use anonymized, aggregated data to improve AI models</li>
              <li>Display your content back to you across devices</li>
            </ul>
            <p className="text-foreground/90 leading-relaxed mt-4">
              We will not share your personal conversations publicly or use them for marketing without your explicit consent.
            </p>

            <h3 className="text-xl font-semibold mt-6 mb-3 text-foreground">7.3 Prohibited Content</h3>
            <p className="text-foreground/90 leading-relaxed mb-4">
              You agree not to use Luna2077 to create, share, or request content that:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-foreground/90">
              <li>Violates any laws or regulations</li>
              <li>Infringes on intellectual property rights</li>
              <li>Contains malware, viruses, or harmful code</li>
              <li>Harasses, threatens, or harms others</li>
              <li>Involves minors in any inappropriate context</li>
              <li>Attempts to exploit or manipulate the AI system</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-display font-semibold mt-8 mb-4 text-foreground">8. Account Responsibilities</h2>
            <p className="text-foreground/90 leading-relaxed mb-4">
              You are responsible for:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-foreground/90">
              <li>Maintaining the confidentiality of your account credentials</li>
              <li>All activities that occur under your account</li>
              <li>Notifying us immediately of any unauthorized access</li>
              <li>Ensuring your payment information is current and accurate</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-display font-semibold mt-8 mb-4 text-foreground">9. Service Availability</h2>
            <p className="text-foreground/90 leading-relaxed mb-4">
              While we strive for 99.9% uptime, we do not guarantee uninterrupted access to Luna2077. The Service may be temporarily unavailable due to:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-foreground/90">
              <li>Scheduled maintenance and updates</li>
              <li>Technical issues or server outages</li>
              <li>Third-party service disruptions</li>
              <li>Force majeure events</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-display font-semibold mt-8 mb-4 text-foreground">10. Intellectual Property</h2>
            <p className="text-foreground/90 leading-relaxed mb-4">
              All content, features, and functionality of Luna2077 (including but not limited to text, graphics, logos, AI models, and software) are owned by Luna2077 and are protected by copyright, trademark, and other intellectual property laws.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-display font-semibold mt-8 mb-4 text-foreground">11. Limitation of Liability</h2>
            <p className="text-foreground/90 leading-relaxed mb-4">
              TO THE MAXIMUM EXTENT PERMITTED BY LAW, LUNA2077 SHALL NOT BE LIABLE FOR:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-foreground/90">
              <li>Indirect, incidental, special, or consequential damages</li>
              <li>Loss of profits, data, or business opportunities</li>
              <li>Damages resulting from AI-generated content or advice</li>
              <li>Unauthorized access to your account or data</li>
              <li>Service interruptions or data loss</li>
            </ul>
            <p className="text-foreground/90 leading-relaxed mt-4">
              Our total liability shall not exceed the amount you paid for the Service in the 12 months preceding the claim.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-display font-semibold mt-8 mb-4 text-foreground">12. Indemnification</h2>
            <p className="text-foreground/90 leading-relaxed mb-4">
              You agree to indemnify and hold harmless Luna2077 from any claims, damages, or expenses arising from your use of the Service, violation of these Terms, or infringement of any third-party rights.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-display font-semibold mt-8 mb-4 text-foreground">13. Termination</h2>
            <p className="text-foreground/90 leading-relaxed mb-4">
              We reserve the right to suspend or terminate your account at our discretion if you:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-foreground/90">
              <li>Violate these Terms of Service</li>
              <li>Engage in fraudulent or illegal activities</li>
              <li>Abuse or exploit the Service</li>
              <li>Fail to pay subscription fees</li>
            </ul>
            <p className="text-foreground/90 leading-relaxed mt-4">
              Upon termination, your right to access the Service will immediately cease, and we may delete your account data.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-display font-semibold mt-8 mb-4 text-foreground">14. Governing Law</h2>
            <p className="text-foreground/90 leading-relaxed mb-4">
              These Terms shall be governed by and construed in accordance with the laws of the State of California, United States, without regard to its conflict of law provisions.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-display font-semibold mt-8 mb-4 text-foreground">15. Dispute Resolution</h2>
            <p className="text-foreground/90 leading-relaxed mb-4">
              Any disputes arising from these Terms or your use of Luna2077 shall be resolved through binding arbitration in accordance with the rules of the American Arbitration Association, rather than in court.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-display font-semibold mt-8 mb-4 text-foreground">16. Changes to Terms</h2>
            <p className="text-foreground/90 leading-relaxed mb-4">
              We may modify these Terms at any time. Material changes will be communicated via email or in-app notification at least 30 days before taking effect. Continued use of the Service after changes constitutes acceptance of the updated Terms.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-display font-semibold mt-8 mb-4 text-foreground">17. Contact Information</h2>
            <p className="text-foreground/90 leading-relaxed mb-4">
              For questions about these Terms of Service, please contact us:
            </p>
            <ul className="list-none space-y-2 text-foreground/90">
              <li><strong>Email:</strong> <a href="mailto:support@luna2077.ai" className="text-primary hover:underline">support@luna2077.ai</a></li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-display font-semibold mt-8 mb-4 text-foreground">18. Severability</h2>
            <p className="text-foreground/90 leading-relaxed mb-4">
              If any provision of these Terms is found to be unenforceable or invalid, that provision shall be limited or eliminated to the minimum extent necessary, and the remaining provisions shall remain in full force and effect.
            </p>
          </section>

          <section className="mb-8">
            <p className="text-foreground/90 leading-relaxed">
              By using Luna2077, you acknowledge that you have read, understood, and agree to be bound by these Terms of Service.
            </p>
          </section>
        </article>
      </div>
    </div>
  );
}
