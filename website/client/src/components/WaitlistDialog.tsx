/* Cinematic Noir Tech - Waitlist Dialog Component
 * Modal dialog for collecting waitlist signups
 * Glassmorphism design with form validation
 */

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Mail, Sparkles } from "lucide-react";

interface WaitlistDialogProps {
  trigger?: React.ReactNode;
  variant?: "default" | "outline" | "accent";
}

export default function WaitlistDialog({ trigger, variant = "accent" }: WaitlistDialogProps) {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!email || !name) {
      toast.error("Please fill in all fields");
      return;
    }

    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      toast.error("Please enter a valid email address");
      return;
    }

    setLoading(true);

    // Simulate API call
    setTimeout(() => {
      toast.success("Welcome to the waitlist!", {
        description: "We'll notify you when Luna2077 launches.",
      });
      setEmail("");
      setName("");
      setLoading(false);
      setOpen(false);
    }, 1000);
  };

  const defaultTrigger = variant === "accent" ? (
    <Button
      size="lg"
      className="bg-accent hover:bg-accent/90 text-accent-foreground font-medium text-base px-8 shadow-lg shadow-accent/30 transition-all duration-300 hover:scale-105"
    >
      <Sparkles className="mr-2 h-5 w-5" />
      Join Waitlist
    </Button>
  ) : (
    <Button
      size="lg"
      variant="outline"
      className="border-primary/50 text-primary hover:bg-primary/10 font-medium text-base px-8 transition-all duration-300"
    >
      <Mail className="mr-2 h-5 w-5" />
      Join Waitlist
    </Button>
  );

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || defaultTrigger}
      </DialogTrigger>
      <DialogContent className="sm:max-w-md bg-card/95 backdrop-blur-xl border-border/50">
        <DialogHeader>
          <DialogTitle className="text-2xl font-display text-center">
            Join the <span className="text-primary">Neural Link</span>
          </DialogTitle>
          <DialogDescription className="text-center pt-2">
            Be among the first to experience the future of AI storytelling.
            We'll notify you when Luna2077 launches.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-6 pt-4">
          <div className="space-y-2">
            <Label htmlFor="name" className="text-foreground">
              Name
            </Label>
            <Input
              id="name"
              type="text"
              placeholder="Enter your name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="bg-background/50 border-border/50 focus:border-primary/50"
              disabled={loading}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="email" className="text-foreground">
              Email
            </Label>
            <Input
              id="email"
              type="email"
              placeholder="your@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="bg-background/50 border-border/50 focus:border-primary/50"
              disabled={loading}
            />
          </div>
          <Button
            type="submit"
            className="w-full bg-accent hover:bg-accent/90 text-accent-foreground shadow-lg shadow-accent/30"
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="animate-pulse">Processing...</span>
              </>
            ) : (
              <>
                <Sparkles className="mr-2 h-4 w-4" />
                Reserve Your Spot
              </>
            )}
          </Button>
          <p className="text-xs text-center text-muted-foreground">
            By joining, you agree to receive updates about Luna2077.
            <br />
            We respect your privacy and won't spam you.
          </p>
        </form>
      </DialogContent>
    </Dialog>
  );
}
