/* Cinematic Noir Tech - Privacy Policy Page
 * Legal document page with clean typography
 */

import Navbar from "@/components/Navbar";
import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";
import { useLocation } from "wouter";

export default function PrivacyPolicy() {
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
          <h1 className="text-4xl font-display font-bold mb-4 text-foreground">Privacy Policy</h1>
          <p className="text-muted-foreground mb-8">Last Updated: February 22, 2026</p>

          <section className="mb-8">
            <h2 className="text-2xl font-display font-semibold mt-8 mb-4 text-foreground">1. Introduction</h2>
            <p className="text-foreground/90 leading-relaxed">
              Welcome to Luna2077 ("Luna", "we", "us", or "our"). We are committed to protecting your privacy and ensuring the security of your personal information. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our AI-powered interactive storytelling platform.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-display font-semibold mt-8 mb-4 text-foreground">2. Information We Collect</h2>
            
            <h3 className="text-xl font-semibold mt-6 mb-3 text-foreground">2.1 Personal Information</h3>
            <p className="text-foreground/90 leading-relaxed mb-4">
              When you create an account or subscribe to our services, we may collect:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-foreground/90">
              <li>Email address</li>
              <li>Username and display name</li>
              <li>Payment information (processed securely through Stripe)</li>
              <li>Subscription status and billing history</li>
            </ul>

            <h3 className="text-xl font-semibold mt-6 mb-3 text-foreground">2.2 User-Generated Content</h3>
            <p className="text-foreground/90 leading-relaxed mb-4">
              We collect and store your interactions with our AI characters, including:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-foreground/90">
              <li>Chat messages and conversation history</li>
              <li>Character preferences and customizations</li>
              <li>Generated visual content and story elements</li>
              <li>User choices and narrative decisions</li>
            </ul>

            <h3 className="text-xl font-semibold mt-6 mb-3 text-foreground">2.3 Technical Information</h3>
            <p className="text-foreground/90 leading-relaxed mb-4">
              We automatically collect certain information about your device and usage:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-foreground/90">
              <li>IP address and device identifiers</li>
              <li>Browser type and operating system</li>
              <li>Usage statistics and interaction patterns</li>
              <li>Cookies and similar tracking technologies</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-display font-semibold mt-8 mb-4 text-foreground">3. How We Use Your Information</h2>
            <p className="text-foreground/90 leading-relaxed mb-4">
              We use the collected information for the following purposes:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-foreground/90">
              <li><strong>Service Delivery:</strong> To provide, maintain, and improve our AI storytelling platform</li>
              <li><strong>Personalization:</strong> To remember your preferences and create personalized experiences</li>
              <li><strong>Memory Retention:</strong> To enable characters to remember your conversation history</li>
              <li><strong>Payment Processing:</strong> To process subscriptions and manage billing through Stripe</li>
              <li><strong>Communication:</strong> To send service updates, security alerts, and support messages</li>
              <li><strong>Analytics:</strong> To understand usage patterns and improve our services</li>
              <li><strong>Security:</strong> To detect, prevent, and address technical issues and fraud</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-display font-semibold mt-8 mb-4 text-foreground">4. Data Privacy and Security</h2>
            
            <h3 className="text-xl font-semibold mt-6 mb-3 text-foreground">4.1 We Do Not Sell Your Data</h3>
            <p className="text-foreground/90 leading-relaxed mb-4">
              <strong>We do not sell, rent, or trade your personal information or conversation data to third parties for marketing purposes.</strong> Your privacy is paramount, and your data belongs to you.
            </p>

            <h3 className="text-xl font-semibold mt-6 mb-3 text-foreground">4.2 Encryption</h3>
            <p className="text-foreground/90 leading-relaxed mb-4">
              All conversations and personal data are encrypted end-to-end using industry-standard encryption protocols. Your data is encrypted both in transit (using TLS/SSL) and at rest.
            </p>

            <h3 className="text-xl font-semibold mt-6 mb-3 text-foreground">4.3 Data Storage</h3>
            <p className="text-foreground/90 leading-relaxed mb-4">
              Your data is stored on secure servers located in the United States. We implement appropriate technical and organizational measures to protect your information against unauthorized access, alteration, disclosure, or destruction.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-display font-semibold mt-8 mb-4 text-foreground">5. Third-Party Services</h2>
            <p className="text-foreground/90 leading-relaxed mb-4">
              We use the following third-party services:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-foreground/90">
              <li><strong>Stripe:</strong> For secure payment processing. Stripe's privacy policy applies to payment data.</li>
              <li><strong>AI Model Providers:</strong> We use third-party AI services to power character interactions. These providers process conversation data according to their privacy policies.</li>
              <li><strong>Analytics Services:</strong> We may use analytics tools to understand usage patterns (anonymized data only).</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-display font-semibold mt-8 mb-4 text-foreground">6. Data Retention</h2>
            <p className="text-foreground/90 leading-relaxed mb-4">
              We retain your personal information and conversation history for as long as your account is active or as needed to provide services. You may request deletion of your data at any time by contacting us at <a href="mailto:support@luna2077.ai" className="text-primary hover:underline">support@luna2077.ai</a>.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-display font-semibold mt-8 mb-4 text-foreground">7. Your Rights</h2>
            <p className="text-foreground/90 leading-relaxed mb-4">
              Depending on your location, you may have the following rights:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-foreground/90">
              <li><strong>Access:</strong> Request a copy of your personal data</li>
              <li><strong>Correction:</strong> Update or correct inaccurate information</li>
              <li><strong>Deletion:</strong> Request deletion of your account and data</li>
              <li><strong>Portability:</strong> Request a copy of your data in a portable format</li>
              <li><strong>Opt-Out:</strong> Unsubscribe from marketing communications</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-display font-semibold mt-8 mb-4 text-foreground">8. Children's Privacy</h2>
            <p className="text-foreground/90 leading-relaxed mb-4">
              Luna2077 is not intended for users under the age of 18. We do not knowingly collect personal information from children. If you believe we have collected information from a child, please contact us immediately.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-display font-semibold mt-8 mb-4 text-foreground">9. International Users</h2>
            <p className="text-foreground/90 leading-relaxed mb-4">
              Luna2077 is operated from the United States. If you are accessing our services from outside the US, please be aware that your information may be transferred to, stored, and processed in the United States where our servers are located.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-display font-semibold mt-8 mb-4 text-foreground">10. Changes to This Policy</h2>
            <p className="text-foreground/90 leading-relaxed mb-4">
              We may update this Privacy Policy from time to time. We will notify you of any changes by posting the new Privacy Policy on this page and updating the "Last Updated" date. Continued use of our services after changes constitutes acceptance of the updated policy.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-display font-semibold mt-8 mb-4 text-foreground">11. Contact Us</h2>
            <p className="text-foreground/90 leading-relaxed mb-4">
              If you have any questions about this Privacy Policy or our data practices, please contact us:
            </p>
            <ul className="list-none space-y-2 text-foreground/90">
              <li><strong>Email:</strong> <a href="mailto:support@luna2077.ai" className="text-primary hover:underline">support@luna2077.ai</a></li>
            </ul>
          </section>
        </article>
      </div>
    </div>
  );
}
