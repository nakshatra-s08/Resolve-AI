import React from 'react'
import {
  Wrench,
  Search,
  MapPin,
  Globe,
  User,
  Mic,
} from 'lucide-react'

interface NavbarProps {
  currentTab: string
  onTabChange: (tab: string) => void
  onNewCaseClick: () => void
  activeCaseId?: string | null
}

export const Navbar: React.FC<NavbarProps> = ({
  currentTab,
  onTabChange,
  onNewCaseClick,
  activeCaseId,
}) => {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 shadow-sm border-b border-[#5B4B8A]/30">
      {/* Top Deep Indigo Brand Bar */}
      <div className="bg-[#312E81] text-white">
        <div className="max-w-[1400px] mx-auto px-4 lg:px-8 h-16 flex items-center justify-between gap-4">
          {/* Logo & Brand */}
          <div
            className="flex items-center gap-3 cursor-pointer select-none"
            onClick={() => onTabChange('home')}
          >
            <div className="w-9 h-9 rounded-lg bg-[#D97757] flex items-center justify-center text-white font-bold shadow-xs">
              <Wrench className="w-5 h-5 text-white" />
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <span className="text-xl font-bold tracking-tight text-white font-['Hanken_Grotesk']">
                  ResolveAI
                </span>
                <span className="text-xs text-[#F0EEFA]/80 border-l border-[#5B4B8A] pl-2 hidden sm:inline">
                  Repair Resolution Assistant
                </span>
              </div>
              <div className="flex items-center gap-1 text-[#F0EEFA]/70 text-xs">
                <MapPin className="w-3 h-3 text-[#E7B76A]" />
                <span>Consumer Dispute & Warranty Workspace</span>
              </div>
            </div>
          </div>

          {/* Search Bar */}
          <div className="flex-1 max-w-xl hidden md:flex items-center">
            <div className="w-full flex rounded-lg overflow-hidden border border-[#5B4B8A] focus-within:ring-2 focus-within:ring-[#8B7BC4] bg-white">
              <button
                type="button"
                className="h-9 px-3 bg-[#F0EEFA] text-[#312E81] text-xs font-semibold flex items-center gap-1 border-r border-[#E4E1E8] hover:bg-[#E4E0F5]"
              >
                <span>Cases</span>
              </button>
              <input
                type="text"
                placeholder="Search cases, service records, warranty clauses..."
                className="w-full h-9 px-3 bg-white text-[#27243A] text-xs focus:outline-none placeholder:text-[#8E8B99]"
              />
              <button
                type="button"
                className="h-9 px-4 bg-[#5B4B8A] hover:bg-[#4B3C73] text-white flex items-center justify-center transition-colors cursor-pointer"
                title="Search"
              >
                <Search className="w-4 h-4 text-white" />
              </button>
            </div>
          </div>

          {/* Right Links & Case Action */}
          <div className="flex items-center gap-3 text-xs">
            <button
              onClick={onNewCaseClick}
              className="h-9 px-3.5 bg-[#D97757] hover:bg-[#B85F44] text-white font-bold text-xs rounded-lg shadow-xs flex items-center gap-1.5 transition-all cursor-pointer"
            >
              <Mic className="w-3.5 h-3.5" />
              <span>New Case</span>
            </button>

            <div className="hidden lg:flex items-center gap-1 text-[#F0EEFA]/80 hover:text-white cursor-pointer px-2 py-1 rounded">
              <Globe className="w-4 h-4 text-[#E7B76A]" />
              <span className="font-semibold text-white">EN-IN</span>
            </div>

            <div className="flex items-center gap-2 pl-2 border-l border-[#5B4B8A]">
              <div className="w-7 h-7 rounded-full bg-[#5B4B8A] flex items-center justify-center text-white">
                <User className="w-4 h-4" />
              </div>
              <div className="hidden sm:flex flex-col text-left leading-tight">
                <span className="text-[#F0EEFA]/70 text-[10px]">Consumer Session</span>
                <span className="font-semibold text-white text-xs">Active Workspace</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Secondary Plum Nav Strip */}
      <div className="bg-[#5B4B8A] text-white border-t border-[#312E81]/40">
        <div className="max-w-[1400px] mx-auto px-4 lg:px-8 h-10 flex items-center justify-between text-xs font-semibold">
          <nav className="flex items-center gap-1 overflow-x-auto no-scrollbar">
            <button
              onClick={() => onTabChange('home')}
              className={`px-3 py-1 rounded-md transition-colors whitespace-nowrap cursor-pointer ${
                currentTab === 'home'
                  ? 'bg-[#312E81] text-white font-bold shadow-xs'
                  : 'text-[#F0EEFA]/80 hover:text-white hover:bg-[#312E81]/50'
              }`}
            >
              Dashboard
            </button>

            <button
              onClick={() => onTabChange('cases')}
              className={`px-3 py-1 rounded-md transition-colors whitespace-nowrap cursor-pointer ${
                currentTab === 'cases'
                  ? 'bg-[#312E81] text-white font-bold shadow-xs'
                  : 'text-[#F0EEFA]/80 hover:text-white hover:bg-[#312E81]/50'
              }`}
            >
              All Cases
            </button>

            {activeCaseId && (
              <button
                onClick={() => onTabChange('case-details')}
                className={`px-3 py-1 rounded-md transition-colors whitespace-nowrap cursor-pointer ${
                  currentTab === 'case-details'
                    ? 'bg-[#312E81] text-white font-bold shadow-xs'
                    : 'text-[#F0EEFA]/80 hover:text-white hover:bg-[#312E81]/50'
                }`}
              >
                Case #{activeCaseId.slice(0, 8)}
              </button>
            )}

            <button
              onClick={() => onTabChange('follow-ups')}
              className={`px-3 py-1 rounded-md transition-colors whitespace-nowrap cursor-pointer ${
                currentTab === 'follow-ups'
                  ? 'bg-[#312E81] text-white font-bold shadow-xs'
                  : 'text-[#F0EEFA]/80 hover:text-white hover:bg-[#312E81]/50'
              }`}
            >
              Scheduled Follow-ups
            </button>
          </nav>

          <div className="hidden sm:flex items-center gap-2 bg-[#312E81]/60 px-2.5 py-1 rounded-md text-[11px] text-[#F0EEFA] border border-[#5B4B8A]">
            <span className="w-2 h-2 rounded-full bg-[#3E7C68] animate-pulse" />
            <span>Voice Intake Ready</span>
          </div>
        </div>
      </div>
    </header>
  )
}
