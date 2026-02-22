/* Cinematic Noir Tech - Navbar Component
 * Sticky glassmorphism navbar with dramatic lighting
 * Orbitron font for logo, subtle backdrop blur
 */

import { Button } from "@/components/ui/button";
import { Menu, X, MessageSquare } from "lucide-react";
import { useState } from "react";

export default function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <nav className="sticky top-0 z-50 border-b border-border/50 backdrop-blur-xl bg-background/80 film-grain">
      <div className="container mx-auto">
        <div className="flex items-center justify-between h-16 lg:h-20">
          {/* Logo */}
          <a href="/" className="flex items-center space-x-2 group">
            <div className="w-8 h-8 rounded bg-primary/20 border border-primary/50 flex items-center justify-center group-hover:bg-primary/30 transition-all duration-300">
              <span className="text-primary font-display font-bold text-sm">L</span>
            </div>
            <span className="text-xl lg:text-2xl font-display font-medium tracking-tight text-foreground">
              Luna2077
            </span>
          </a>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-8">
            <a
              href="/#features"
              className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors duration-300"
            >
              Features
            </a>
            <a
              href="/#characters"
              className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors duration-300"
            >
              Characters
            </a>
            <a
              href="/#pricing"
              className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors duration-300"
            >
              Pricing
            </a>
            <a
              href="/#about"
              className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors duration-300"
            >
              About
            </a>
            <Button
              variant="outline"
              className="border-border/50 hover:border-primary/50 hover:text-primary transition-all duration-300"
              onClick={() => window.open('https://t.me/Project_Waifu_Mio_bot', '_blank')}
            >
              <MessageSquare className="mr-2 h-4 w-4" />
              Start Bot
            </Button>
          </div>

          {/* Mobile Menu Button */}
          <button
            className="md:hidden p-2 text-foreground hover:text-primary transition-colors"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle menu"
          >
            {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden py-4 space-y-4 border-t border-border/50 bg-card/50 backdrop-blur-xl animate-in slide-in-from-top duration-300">
            <a
              href="/#features"
              className="block px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
              onClick={() => setMobileMenuOpen(false)}
            >
              Features
            </a>
            <a
              href="/#characters"
              className="block px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
              onClick={() => setMobileMenuOpen(false)}
            >
              Characters
            </a>
            <a
              href="/#pricing"
              className="block px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
              onClick={() => setMobileMenuOpen(false)}
            >
              Pricing
            </a>
            <a
              href="/#about"
              className="block px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
              onClick={() => setMobileMenuOpen(false)}
            >
              About
            </a>
            <div className="px-4">
              <Button 
                variant="outline" 
                className="w-full border-border/50"
                onClick={() => window.open('https://t.me/Project_Waifu_Mio_bot', '_blank')}
              >
                <MessageSquare className="mr-2 h-4 w-4" />
                Start Telegram Bot
              </Button>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}
