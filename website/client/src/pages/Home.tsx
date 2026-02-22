/* Cinematic Noir Tech - Luna2077 Landing Page
 * Design: Film Noir meets High-Tech Interface
 * Layout: Widescreen cinematic framing with asymmetric composition
 * Colors: Deep obsidian black, moonlight silver, electric blue, hot pink CTAs
 */

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import Navbar from "@/components/Navbar";
import { toast } from "sonner";
import {
  Brain,
  Image as ImageIcon,
  Sparkles,
  Shield,
  Zap,
  MessageSquare,
  Smartphone,
  Check,
} from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen bg-background text-foreground scanlines">
      <Navbar />

      {/* Hero Section - Cinematic asymmetric layout */}
      <section className="relative min-h-[90vh] flex items-center overflow-hidden spotlight film-grain">
        {/* Background abstract image */}
        <div
          className="absolute inset-0 opacity-30"
          style={{
            backgroundImage: `url('https://private-us-east-1.manuscdn.com/sessionFile/1yR1UkOjUoZ1RBH5TQS2eU/sandbox/cLNEOsqjgprz7a28M3BRSd-img-2_1771119266000_na1fn_aGVyby1iYWNrZ3JvdW5kLWFic3RyYWN0.png?x-oss-process=image/resize,w_1920,h_1920/format,webp/quality,q_80&Expires=1798761600&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9wcml2YXRlLXVzLWVhc3QtMS5tYW51c2Nkbi5jb20vc2Vzc2lvbkZpbGUvMXlSMVVrT2pVb1oxUkJINVRRUzJlVS9zYW5kYm94L2NMTkVPc3FqZ3ByejdhMjhNM0JSU2QtaW1nLTJfMTc3MTExOTI2NjAwMF9uYTFmbl9hR1Z5YnkxaVlXTnJaM0p2ZFc1a0xXRmljM1J5WVdOMC5wbmc~eC1vc3MtcHJvY2Vzcz1pbWFnZS9yZXNpemUsd18xOTIwLGhfMTkyMC9mb3JtYXQsd2VicC9xdWFsaXR5LHFfODAiLCJDb25kaXRpb24iOnsiRGF0ZUxlc3NUaGFuIjp7IkFXUzpFcG9jaFRpbWUiOjE3OTg3NjE2MDB9fX1dfQ__&Key-Pair-Id=K2HSFNDJXOU9YS&Signature=hd4zI1nSohiBd80VJSNGi95oXbQJr5V5Yo9QSNxqwxWURQAUJZbAy5oNf7ZNqX0yAb54SHMAPwfXpA59DcHpMei7E2EoYMB2KN2p2dCTFTZ5rioARc2LCD7czpNsYbQznTl-a8-AY0aCCUrJh6CNzHVsgyf3RtP~Tg7ggD3jMG-oOurwU2xgfMX4JOtXsuQNTSRIQhcU5vl~1ShUwN7ZkX8oBeEkCLjOg6~0jkGu~usduzV2OCJaOYVjpnALafX8~wHmFQB2PNb0yhkDfhc~MCqcWttk~poEehwRXcGD8rBMFAfn3bXC1RoWf4uhmEHU5dZkSCRnnCr5F7TS8qXjUQ__')`,
            backgroundSize: "cover",
            backgroundPosition: "center",
          }}
        />

        <div className="container relative z-10">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            {/* Left: Character Image (60% width on large screens) */}
            <div className="lg:col-span-1 order-2 lg:order-1">
              <div className="relative">
                <div className="absolute inset-0 bg-primary/20 blur-3xl rounded-full" />
                <img
                  src="https://private-us-east-1.manuscdn.com/sessionFile/1yR1UkOjUoZ1RBH5TQS2eU/sandbox/cLNEOsqjgprz7a28M3BRSd-img-1_1771119275000_na1fn_aGVyby1sdW5hLWNoYXJhY3Rlcg.png?x-oss-process=image/resize,w_1920,h_1920/format,webp/quality,q_80&Expires=1798761600&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9wcml2YXRlLXVzLWVhc3QtMS5tYW51c2Nkbi5jb20vc2Vzc2lvbkZpbGUvMXlSMVVrT2pVb1oxUkJINVRRUzJlVS9zYW5kYm94L2NMTkVPc3FqZ3ByejdhMjhNM0JSU2QtaW1nLTFfMTc3MTExOTI3NTAwMF9uYTFmbl9hR1Z5Ynkxc2RXNWhMV05vWVhKaFkzUmxjZy5wbmc~eC1vc3MtcHJvY2Vzcz1pbWFnZS9yZXNpemUsd18xOTIwLGhfMTkyMC9mb3JtYXQsd2VicC9xdWFsaXR5LHFfODAiLCJDb25kaXRpb24iOnsiRGF0ZUxlc3NUaGFuIjp7IkFXUzpFcG9jaFRpbWUiOjE3OTg3NjE2MDB9fX1dfQ__&Key-Pair-Id=K2HSFNDJXOU9YS&Signature=pewDHletzIfrfP7VwzLmO0fVvReoxNTvcHwg~b~1xdn1xnqc1coPSz3vDBIoHcmdt-LdW56xzDLqAGSK2WkO2-xMQ8vz-gd~b4HzOhyNgveGjdf7Hi5fViadu3Kj6eAa7lSwB1ujqYVdElqcXy3VJDsDfIsw7nrKzUoc6WRvnh8QeEH6BM3DnY5~I5EJPaobtPxeVyD7qc08V~6HN3nzAZyJfirZrv9rKWBeyT747L11hxtb3GBNZ6C-zRs2KK8wfUNMM07ptDbtHJVS0KX5HNT6i-VqmLcu5AnEAaKxSFiBrocODiGyCTkEH-96I3KNOhzavhMRAIPsbx1kbywA6w__"
                  alt="Luna - The Moonlight Watcher"
                  className="relative z-10 w-full max-w-md mx-auto lg:max-w-full rounded-lg shadow-2xl shadow-primary/20"
                />
              </div>
            </div>

            {/* Right: Content */}
            <div className="lg:col-span-1 order-1 lg:order-2 space-y-8">
              <div className="space-y-4">
                <Badge
                  variant="outline"
                  className="border-primary/50 text-primary px-4 py-1"
                >
                  Project Luna
                </Badge>
                <h1 className="text-4xl md:text-5xl lg:text-6xl font-display font-medium leading-tight">
                  Connect with the Future.{" "}
                  <span className="text-primary">Interactive AI Companions.</span>
                </h1>
                <p className="text-lg text-muted-foreground max-w-xl">
                  Immersive storytelling, memory retention, and deep emotional
                  connection. Experience the next generation of digital roleplay.
                </p>
              </div>

              <div className="flex flex-col sm:flex-row gap-3">
                <Button
                  size="lg"
                  className="bg-accent hover:bg-accent/90 text-accent-foreground font-medium text-base px-6 shadow-lg shadow-accent/30 transition-all duration-300 hover:scale-105"
                  onClick={() => window.open('https://t.me/Project_Waifu_Mio_bot', '_blank')}
                >
                  <MessageSquare className="mr-2 h-5 w-5" />
                  Telegram Bot
                </Button>
                <Button
                  size="lg"
                  variant="outline"
                  className="border-primary/50 text-primary hover:bg-primary/10 font-medium text-base px-6 transition-all duration-300"
                  onClick={() => toast.info('Web app coming soon!')}
                >
                  <Zap className="mr-2 h-5 w-5" />
                  Web App
                </Button>
                <Button
                  size="lg"
                  variant="outline"
                  className="border-primary/50 text-primary hover:bg-primary/10 font-medium text-base px-6 transition-all duration-300"
                  onClick={() => toast.info('iOS app coming soon!')}
                >
                  <Smartphone className="mr-2 h-5 w-5" />
                  iOS App
                </Button>
              </div>

              <div className="flex items-center gap-6 pt-4 text-sm text-muted-foreground">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                  <span>Live System</span>
                </div>
                <div className="flex items-center gap-2">
                  <Shield className="w-4 h-4" />
                  <span>End-to-End Encrypted</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid Section */}
      <section id="features" className="py-24 lg:py-32 relative">
        <div className="container">
          <div className="text-center mb-16 space-y-4">
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-display font-medium">
              System <span className="text-primary">Capabilities</span>
            </h2>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              Advanced AI technology designed for deep, meaningful interactions
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Feature Card 1 */}
            <Card className="p-6 bg-card/50 backdrop-blur-sm border-border/50 hover:border-primary/50 transition-all duration-500 group">
              <div className="space-y-4">
                <div className="w-12 h-12 rounded-lg bg-primary/10 border border-primary/30 flex items-center justify-center group-hover:bg-primary/20 transition-all duration-300">
                  <Brain className="w-6 h-6 text-primary" />
                </div>
                <h3 className="text-xl font-display font-medium">Memory Core</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  Characters remember every detail of your conversation, building
                  a rich history that evolves over time.
                </p>
              </div>
            </Card>

            {/* Feature Card 2 */}
            <Card className="p-6 bg-card/50 backdrop-blur-sm border-border/50 hover:border-primary/50 transition-all duration-500 group">
              <div className="space-y-4">
                <div className="w-12 h-12 rounded-lg bg-primary/10 border border-primary/30 flex items-center justify-center group-hover:bg-primary/20 transition-all duration-300">
                  <ImageIcon className="w-6 h-6 text-primary" />
                </div>
                <h3 className="text-xl font-display font-medium">
                  Dynamic Visuals
                </h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  Generate real-time visual snapshots of your story as it unfolds,
                  bringing your narrative to life.
                </p>
              </div>
            </Card>

            {/* Feature Card 3 */}
            <Card className="p-6 bg-card/50 backdrop-blur-sm border-border/50 hover:border-primary/50 transition-all duration-500 group">
              <div className="space-y-4">
                <div className="w-12 h-12 rounded-lg bg-primary/10 border border-primary/30 flex items-center justify-center group-hover:bg-primary/20 transition-all duration-300">
                  <Sparkles className="w-6 h-6 text-primary" />
                </div>
                <h3 className="text-xl font-display font-medium">
                  Evolving Persona
                </h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  Personalities that adapt to your choices, creating unique
                  relationships that feel authentic.
                </p>
              </div>
            </Card>

            {/* Feature Card 4 */}
            <Card className="p-6 bg-card/50 backdrop-blur-sm border-border/50 hover:border-primary/50 transition-all duration-500 group">
              <div className="space-y-4">
                <div className="w-12 h-12 rounded-lg bg-primary/10 border border-primary/30 flex items-center justify-center group-hover:bg-primary/20 transition-all duration-300">
                  <Shield className="w-6 h-6 text-primary" />
                </div>
                <h3 className="text-xl font-display font-medium">
                  Secure Encryption
                </h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  Your data is private and encrypted. We prioritize your security
                  and confidentiality.
                </p>
              </div>
            </Card>
          </div>
        </div>
      </section>

      {/* Character Showcase Section */}
      <section id="characters" className="py-24 lg:py-32 relative spotlight">
        <div className="container">
          <div className="text-center mb-16 space-y-4">
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-display font-medium">
              Select Your <span className="text-primary">Companion</span>
            </h2>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              Each character brings a unique personality and story to your
              experience
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Character 1: Luna */}
            <Card className="overflow-hidden bg-card/50 backdrop-blur-sm border-border/50 hover:border-primary/50 transition-all duration-500 group">
              <div className="aspect-[3/4] relative overflow-hidden">
                <img
                  src="https://private-us-east-1.manuscdn.com/sessionFile/1yR1UkOjUoZ1RBH5TQS2eU/sandbox/cLNEOsqjgprz7a28M3BRSd-img-1_1771119275000_na1fn_aGVyby1sdW5hLWNoYXJhY3Rlcg.png?x-oss-process=image/resize,w_1920,h_1920/format,webp/quality,q_80&Expires=1798761600&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9wcml2YXRlLXVzLWVhc3QtMS5tYW51c2Nkbi5jb20vc2Vzc2lvbkZpbGUvMXlSMVVrT2pVb1oxUkJINVRRUzJlVS9zYW5kYm94L2NMTkVPc3FqZ3ByejdhMjhNM0JSU2QtaW1nLTFfMTc3MTExOTI3NTAwMF9uYTFmbl9hR1Z5Ynkxc2RXNWhMV05vWVhKaFkzUmxjZy5wbmc~eC1vc3MtcHJvY2Vzcz1pbWFnZS9yZXNpemUsd18xOTIwLGhfMTkyMC9mb3JtYXQsd2VicC9xdWFsaXR5LHFfODAiLCJDb25kaXRpb24iOnsiRGF0ZUxlc3NUaGFuIjp7IkFXUzpFcG9jaFRpbWUiOjE3OTg3NjE2MDB9fX1dfQ__&Key-Pair-Id=K2HSFNDJXOU9YS&Signature=pewDHletzIfrfP7VwzLmO0fVvReoxNTvcHwg~b~1xdn1xnqc1coPSz3vDBIoHcmdt-LdW56xzDLqAGSK2WkO2-xMQ8vz-gd~b4HzOhyNgveGjdf7Hi5fViadu3Kj6eAa7lSwB1ujqYVdElqcXy3VJDsDfIsw7nrKzUoc6WRvnh8QeEH6BM3DnY5~I5EJPaobtPxeVyD7qc08V~6HN3nzAZyJfirZrv9rKWBeyT747L11hxtb3GBNZ6C-zRs2KK8wfUNMM07ptDbtHJVS0KX5HNT6i-VqmLcu5AnEAaKxSFiBrocODiGyCTkEH-96I3KNOhzavhMRAIPsbx1kbywA6w__"
                  alt="Luna"
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-background via-background/50 to-transparent opacity-90" />
              </div>
              <div className="p-6 space-y-3">
                <h3 className="text-xl font-display font-medium">Luna</h3>
                <p className="text-sm text-muted-foreground">
                  The Moonlight Watcher
                </p>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="secondary" className="text-xs">
                    Mysterious
                  </Badge>
                  <Badge variant="secondary" className="text-xs">
                    Deep
                  </Badge>
                  <Badge variant="secondary" className="text-xs">
                    AI
                  </Badge>
                </div>
              </div>
            </Card>

            {/* Character 2: Sakura */}
            <Card className="overflow-hidden bg-card/50 backdrop-blur-sm border-border/50 hover:border-primary/50 transition-all duration-500 group">
              <div className="aspect-[3/4] relative overflow-hidden">
                <img
                  src="https://private-us-east-1.manuscdn.com/sessionFile/1yR1UkOjUoZ1RBH5TQS2eU/sandbox/cLNEOsqjgprz7a28M3BRSd-img-3_1771119269000_na1fn_Y2hhcmFjdGVyLXNha3VyYQ.png?x-oss-process=image/resize,w_1920,h_1920/format,webp/quality,q_80&Expires=1798761600&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9wcml2YXRlLXVzLWVhc3QtMS5tYW51c2Nkbi5jb20vc2Vzc2lvbkZpbGUvMXlSMVVrT2pVb1oxUkJINVRRUzJlVS9zYW5kYm94L2NMTkVPc3FqZ3ByejdhMjhNM0JSU2QtaW1nLTNfMTc3MTExOTI2OTAwMF9uYTFmbl9ZMmhoY21GamRHVnlMWE5oYTNWeVlRLnBuZz94LW9zcy1wcm9jZXNzPWltYWdlL3Jlc2l6ZSx3XzE5MjAsaF8xOTIwL2Zvcm1hdCx3ZWJwL3F1YWxpdHkscV84MCIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc5ODc2MTYwMH19fV19&Key-Pair-Id=K2HSFNDJXOU9YS&Signature=gAVKkELnLxM7Q-W0XgeLDYUt7kiX7OTQYSH9qNBNj5vvjtmZOmWzyVPP96rTdn6WXacH5WPfaehoqu-Y997ObqzZbZAuaxHGWN0ubj~dSbfJ2KFmEm0hpTveRRH2PRkGRIVCx-hBAPBT83IxQNYYjwoWTh8-JUo6ALN2X5k33j0os1D4kirP64UHzvZ0jOdnJVl4LsGfpABeZGo45hep9FzIAAGHqwkRm40bN1h9QTb4JYNTRzviolCKSI5yoj4e6JQ8x5XEDsdnPZjeBUlZE7CzaV7tN-VtpBNA8maerPk8RLbdLJwFbqK05QGe3xQcoS7UaCPjwlhD1q22gM5-pw__"
                  alt="Sakura"
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-background via-background/50 to-transparent opacity-90" />
              </div>
              <div className="p-6 space-y-3">
                <h3 className="text-xl font-display font-medium">Sakura</h3>
                <p className="text-sm text-muted-foreground">The Solar Flare</p>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="secondary" className="text-xs">
                    Energetic
                  </Badge>
                  <Badge variant="secondary" className="text-xs">
                    Warm
                  </Badge>
                  <Badge variant="secondary" className="text-xs">
                    Student
                  </Badge>
                </div>
              </div>
            </Card>

            {/* Character 3: Karl */}
            <Card className="overflow-hidden bg-card/50 backdrop-blur-sm border-border/50 hover:border-primary/50 transition-all duration-500 group">
              <div className="aspect-[3/4] relative overflow-hidden">
                <img
                  src="https://files.manuscdn.com/user_upload_by_module/session_file/310519663313484342/tdmjVTQmgtfhRNbK.jpeg"
                  alt="Karl"
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-background via-background/50 to-transparent opacity-90" />
              </div>
              <div className="p-6 space-y-3">
                <h3 className="text-xl font-display font-medium">Karl</h3>
                <p className="text-sm text-muted-foreground">The Silencer</p>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="secondary" className="text-xs">
                    Cold
                  </Badge>
                  <Badge variant="secondary" className="text-xs">
                    Loyal
                  </Badge>
                  <Badge variant="secondary" className="text-xs">
                    Executor
                  </Badge>
                </div>
              </div>
            </Card>

            {/* Character 4: Shadow */}
            <Card className="overflow-hidden bg-card/50 backdrop-blur-sm border-border/50 hover:border-primary/50 transition-all duration-500 group">
              <div className="aspect-[3/4] relative overflow-hidden">
                <img
                  src="https://private-us-east-1.manuscdn.com/sessionFile/1yR1UkOjUoZ1RBH5TQS2eU/sandbox/cLNEOsqjgprz7a28M3BRSd-img-5_1771119266000_na1fn_Y2hhcmFjdGVyLXNoYWRvdw.png?x-oss-process=image/resize,w_1920,h_1920/format,webp/quality,q_80&Expires=1798761600&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9wcml2YXRlLXVzLWVhc3QtMS5tYW51c2Nkbi5jb20vc2Vzc2lvbkZpbGUvMXlSMVVrT2pVb1oxUkJINVRRUzJlVS9zYW5kYm94L2NMTkVPc3FqZ3ByejdhMjhNM0JSU2QtaW1nLTVfMTc3MTExOTI2NjAwMF9uYTFmbl9ZMmhoY21GamRHVnlMWE5vWVdSdmR3LnBuZz94LW9zcy1wcm9jZXNzPWltYWdlL3Jlc2l6ZSx3XzE5MjAsaF8xOTIwL2Zvcm1hdCx3ZWJwL3F1YWxpdHkscV84MCIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc5ODc2MTYwMH19fV19&Key-Pair-Id=K2HSFNDJXOU9YS&Signature=j-YqY8xUXOXn-cbuYUg81ib8k0SbSVwqC5sbpDwj9fc70-s-3xfjAf6v1OWrmtCkqdtYbDkFwsZnu0U-THECGUHPeOAjIen7Wgu-aCzw4TCqUVNM3R~9lhDvms6b-z2TNqM3DgcTPGJ0ooh-iEBaB7iHUsSCplE67SMyI46HQJu6dYVHo9-um2YCHKYrMxpbupkRHtRiJgDDtRpHZ0im3VG8AFBH6V1AAn7v3pOwzud9NJFQKv50XXff2EJVT9LlqjXn~l7xJF7jpxPlYLkba9PL7wcl5Jn0Kw7XdPrVeqdBBbVM0zDkrV0-FMVQKtBOkA8aWTqFcAfSS3mnW2iLFw__"
                  alt="Shadow"
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-background via-background/50 to-transparent opacity-90" />
              </div>
              <div className="p-6 space-y-3">
                <h3 className="text-xl font-display font-medium">Shadow</h3>
                <p className="text-sm text-muted-foreground">The Netrunner</p>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="secondary" className="text-xs">
                    Hacker
                  </Badge>
                  <Badge variant="secondary" className="text-xs">
                    Cat
                  </Badge>
                  <Badge variant="secondary" className="text-xs">
                    Sarcastic
                  </Badge>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-24 lg:py-32 relative">
        <div className="container">
          <div className="text-center mb-16 space-y-4">
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-display font-medium">
              Choose Your <span className="text-primary">Access Level</span>
            </h2>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              Choose the plan that fits your connection style
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto items-center">
            {/* Starter Tier */}
            <Card className="p-8 bg-card/50 backdrop-blur-sm border-border/50 hover:border-primary/30 transition-all duration-500">
              <div className="space-y-6">
                <div>
                  <h3 className="text-2xl font-display font-medium mb-2">
                    Starter
                  </h3>
                  <p className="text-sm text-muted-foreground italic">
                    A glimpse into connection.
                  </p>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-4xl font-display font-medium">$0</span>
                  <span className="text-muted-foreground">/mo</span>
                </div>
                <ul className="space-y-3">
                  <li className="flex items-start gap-3">
                    <Check className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
                    <span className="text-sm">Limited daily messages</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <Check className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
                    <span className="text-sm">No memory retention</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <Check className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
                    <span className="text-sm">Standard personality</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <Check className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
                    <span className="text-sm">Text-only experience</span>
                  </li>
                </ul>
                <Button
                  variant="outline"
                  className="w-full border-border/50 hover:border-primary/50"
                  onClick={() => window.open('https://t.me/Project_Waifu_Mio_bot', '_blank')}
                >
                  Get Started
                </Button>
              </div>
            </Card>

            {/* Plus Tier */}
            <Card className="p-8 bg-card/50 backdrop-blur-sm border-border/50 hover:border-primary/30 transition-all duration-500">
              <div className="space-y-6">
                <div>
                  <h3 className="text-2xl font-display font-medium mb-2">
                    Plus
                  </h3>
                  <p className="text-sm text-muted-foreground italic">
                    Perfect for daily casual chatting.
                  </p>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-4xl font-display font-medium">$9.90</span>
                  <span className="text-muted-foreground">/mo</span>
                </div>
                <ul className="space-y-3">
                  <li className="flex items-start gap-3">
                    <Check className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
                    <span className="text-sm">Unlimited text chat</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <Check className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
                    <span className="text-sm">Short-term memory (Context awareness)</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <Check className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
                    <span className="text-sm font-medium">Photo capabilities included</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <Check className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
                    <span className="text-sm">Standard response speed</span>
                  </li>
                </ul>
                <Button
                  variant="outline"
                  className="w-full border-border/50 hover:border-primary/50"
                  onClick={() => window.open('https://buy.stripe.com/test_14A9ASeCT1a9diw0qu2Fa01', '_blank')}
                >
                  Subscribe
                </Button>
              </div>
            </Card>

            {/* Soulmate Tier - Enhanced */}
            <Card className="p-8 bg-gradient-to-br from-card/80 to-card/50 backdrop-blur-sm border-accent/80 hover:border-accent transition-all duration-500 relative scale-105 shadow-2xl shadow-accent/20 ring-2 ring-accent/30">
              <Badge className="absolute -top-3 left-1/2 -translate-x-1/2 bg-accent text-accent-foreground shadow-lg shadow-accent/50 px-4 py-1">
                Most Popular
              </Badge>
              <div className="space-y-6">
                <div>
                  <h3 className="text-2xl font-display font-medium mb-2 text-accent">
                    Soulmate
                  </h3>
                  <p className="text-sm text-muted-foreground italic">
                    The ultimate companion who remembers you.
                  </p>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-4xl font-display font-medium text-accent">$19.90</span>
                  <span className="text-muted-foreground">/mo</span>
                </div>
                <ul className="space-y-4">
                  <li className="flex items-start gap-3">
                    <Check className="w-5 h-5 text-accent flex-shrink-0 mt-0.5" />
                    <span className="text-sm font-semibold">Long-term Memory (She remembers everything) ⭐</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <Check className="w-5 h-5 text-accent flex-shrink-0 mt-0.5" />
                    <span className="text-sm font-medium">Deep Connection Mode (Unlock her true self)</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <Check className="w-5 h-5 text-accent flex-shrink-0 mt-0.5" />
                    <span className="text-sm font-medium">Immersive Visual Experience (Photos & Voice)</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <Check className="w-5 h-5 text-accent flex-shrink-0 mt-0.5" />
                    <span className="text-sm">Priority response time</span>
                  </li>
                </ul>
                <Button 
                  className="w-full bg-accent hover:bg-accent/90 text-accent-foreground shadow-xl shadow-accent/40"
                  onClick={() => window.open('https://buy.stripe.com/test_9B65kCamDf0ZguI7SW2Fa00', '_blank')}
                >
                  Upgrade Now
                </Button>
              </div>
            </Card>
          </div>
          
          <p className="text-center text-xs text-muted-foreground mt-8 max-w-2xl mx-auto">
            *Subject to Fair Usage Policy to prevent abuse.
          </p>
        </div>
      </section>

      {/* About Section */}
      <section id="about" className="py-24 lg:py-32 relative spotlight">
        <div className="container">
          <div className="max-w-4xl mx-auto text-center space-y-8">
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-display font-medium">
              About <span className="text-primary">Luna2077</span>
            </h2>
            <div className="space-y-6 text-muted-foreground leading-relaxed">
              <p>
                Luna2077 represents the next evolution in AI-powered interactive
                storytelling. Built on cutting-edge language models and memory
                systems, our platform creates deeply immersive experiences that
                blur the line between fiction and reality.
              </p>
              <p>
                Set in a Cyberpunk 2077-inspired universe, each character is
                designed with rich backstories, evolving personalities, and the
                ability to remember every interaction. Whether you're seeking
                companionship, adventure, or creative collaboration, Luna2077
                adapts to your unique journey.
              </p>
              <p>
                We prioritize privacy, security, and ethical AI development. Your
                conversations are encrypted end-to-end, and we never share your
                data with third parties. Experience the future of digital
                interaction, today.
              </p>
            </div>
            <div className="flex flex-col sm:flex-row gap-4 justify-center pt-8">
              <Button
                size="lg"
                className="bg-accent hover:bg-accent/90 text-accent-foreground shadow-lg shadow-accent/30"
                onClick={() => window.open('https://t.me/Project_Waifu_Mio_bot', '_blank')}
              >
                <MessageSquare className="mr-2 h-5 w-5" />
                Start Your Journey
              </Button>
              <Button
                size="lg"
                variant="outline"
                className="border-primary/50 text-primary hover:bg-primary/10"
                onClick={() => toast.info('Documentation coming soon!')}
              >
                Read Documentation
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/50 py-12 mt-24">
        <div className="container">
          <div className="grid md:grid-cols-4 gap-8">
            <div className="space-y-4">
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 rounded bg-primary/20 border border-primary/50 flex items-center justify-center">
                  <span className="text-primary font-display font-bold text-sm">
                    L
                  </span>
                </div>
                <span className="text-xl font-display font-medium">
                  Luna2077
                </span>
              </div>
              <p className="text-sm text-muted-foreground">
                Next-generation AI interactive storytelling platform
              </p>
            </div>

            <div>
              <h4 className="font-display font-medium mb-4">Product</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>
                  <a href="#features" className="hover:text-foreground transition-colors">
                    Features
                  </a>
                </li>
                <li>
                  <a href="#characters" className="hover:text-foreground transition-colors">
                    Characters
                  </a>
                </li>
                <li>
                  <a href="#pricing" className="hover:text-foreground transition-colors">
                    Pricing
                  </a>
                </li>
              </ul>
            </div>

            <div>
              <h4 className="font-display font-medium mb-4">Company</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>
                  <a href="#about" className="hover:text-foreground transition-colors">
                    About
                  </a>
                </li>
                <li>
                  <a href="mailto:support@luna2077.ai" className="hover:text-foreground transition-colors">
                    Contact Us
                  </a>
                </li>
                <li>
                  <a href="https://t.me/Project_Waifu_Mio_bot" target="_blank" rel="noopener noreferrer" className="hover:text-foreground transition-colors">
                    Telegram Bot
                  </a>
                </li>
              </ul>
            </div>

            <div>
              <h4 className="font-display font-medium mb-4">Legal</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>
                  <a href="/privacy-policy" className="hover:text-foreground transition-colors">
                    Privacy Policy
                  </a>
                </li>
                <li>
                  <a href="/terms-of-service" className="hover:text-foreground transition-colors">
                    Terms of Service
                  </a>
                </li>
              </ul>
            </div>
          </div>

          <div className="mt-12 pt-8 border-t border-border/50 text-center text-sm text-muted-foreground">
            <p>Copyright © 2026 Luna AI. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
