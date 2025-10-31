import Button from "./Button.jsx";
import Card, { FeatureCard } from "./Card.jsx";

const FEATURES = [
  {
    title: "Smart Retrieval",
    description: "Gets relevant queries from FAISS vector index to inform SQL generation."
  },
  {
    title: "Schema-Aware",
    description: "Injects schema and LookML join hints for accurate SQL generation."
  },
  {
    title: "Validated & Secure",
    description: "Schema-strict validation ensures safety before execution."
  },
  {
    title: "BigQuery Ready",
    description: "Execution with cost controls including dry run and limits."
  }
];

function QuickActionButtons() {
  return (
    <div className="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-3">
      <Button 
        variant="primary" 
        size="md"
        onClick={() => window.location.hash = '#chat'}
      >
        Start Chat
      </Button>
      <Button 
        variant="secondary" 
        size="md"
        onClick={() => window.location.hash = '#data'}
      >
        View Data
      </Button>
    </div>
  );
}

export default function Introduction() {
  return (
    <div className="space-y-8">
      {/* Clean Hero Section */}
      <div className="text-center max-w-3xl mx-auto animate-fade-in-up">
        <h1 className="typography-hero mb-4">
          Welcome to SQL RAG
        </h1>
        
        <p className="typography-body mb-6 max-w-xl mx-auto">
          Ask questions in natural language and get accurate, context-aware SQL queries powered by AI.
        </p>
        
        <div className="mb-8">
          <QuickActionButtons />
        </div>
        
        <div className="flex items-center justify-center space-x-6">
          <div className="text-center">
            <p className="typography-heading text-2xl font-bold text-blue-400">98.5%</p>
            <p className="typography-caption text-xs">Success</p>
          </div>
          <div className="text-center">
            <p className="typography-heading text-2xl font-bold text-green-400">1.2s</p>
            <p className="typography-caption text-xs">Avg Time</p>
          </div>
          <div className="text-center">
            <p className="typography-heading text-2xl font-bold text-purple-400">50+</p>
            <p className="typography-caption text-xs">Samples</p>
          </div>
        </div>
      </div>

      {/* How It Works - No Icons */}
      <div className="max-w-3xl mx-auto animate-fade-in-up stagger-1">
        <Card className="bg-gradient-to-br from-gray-900 to-gray-800 border-gray-700">
          <div className="text-center mb-6">
            <h2 className="typography-heading mb-3">How It Works</h2>
            <p className="typography-body text-sm">
              Retrieves relevant context, generates accurate SQL, validates, and executes safely.
            </p>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { step: 1, title: "Process", desc: "Understand question" },
              { step: 2, title: "Retrieve", desc: "Find examples" },
              { step: 3, title: "Generate", desc: "Create SQL" },
              { step: 4, title: "Execute", desc: "Run safely" }
            ].map((item, index) => (
              <div key={index} className="text-center">
                <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center mx-auto mb-2">
                  <span className="text-white font-bold text-xs">{item.step}</span>
                </div>
                <h3 className="typography-subheading text-xs mb-1">{item.title}</h3>
                <p className="typography-caption text-xs">{item.desc}</p>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Features Grid - No Icons */}
      <div className="max-w-5xl mx-auto animate-fade-in-up stagger-2">
        <div className="text-center mb-8">
          <h2 className="typography-heading mb-3">Key Features</h2>
          <p className="typography-body text-sm max-w-xl mx-auto">
            Modern architecture powered by Google's Gemini AI for exceptional performance.
          </p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {FEATURES.map((feature, index) => (
            <FeatureCard
              key={index}
              title={feature.title}
              description={feature.description}
              className="animate-fade-in-up"
              style={{ animationDelay: `${index * 0.08}s` }}
            />
          ))}
        </div>
      </div>

      {/* Tips Section - No Icons */}
      <div className="max-w-3xl mx-auto animate-fade-in-up stagger-3">
        <Card className="bg-blue-900/20 border-blue-800/50">
          <div className="flex items-start space-x-3">
            <div className="flex-shrink-0">
              <div className="w-6 h-6 bg-blue-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-xs">i</span>
              </div>
            </div>
            <div className="flex-1">
              <h3 className="typography-subheading mb-2 text-sm">Quick Start</h3>
              <div className="space-y-2 mb-4">
                <p className="typography-body text-sm">
                  Explore the <strong>Data</strong> tab to understand available tables.
                </p>
                <p className="typography-body text-sm">
                  Use <code className="bg-gray-800 px-2 py-0.5 rounded text-green-300 text-xs">@create</code> for structured SQL.
                </p>
                <p className="typography-body text-sm">
                  Try <strong>Chat</strong> for natural language questions.
                </p>
              </div>
              
              <Button variant="accent" size="sm" onClick={() => window.location.hash = '#chat'}>
                Try Now →
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}