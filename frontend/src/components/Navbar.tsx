import React from 'react'
import {
  Wrench,
  Search,
  MapPin,
  Globe,
  User,
  PlusCircle,
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
    <header className="fixed top-0 left-0 right-0 z-50 shadow-md">
      {/* Top Main Dark Bar */}
      <div className="bg-[#131921] text-white">
        <div className="max-w-[1400px] mx-auto px-4 lg:px-8 h-16 flex items-center justify-between gap-4">
          {/* Logo & Brand */}
          <div
            className="flex items-center gap-3 cursor-pointer select-none"
            onClick={() => onTabChange('home')}
          >
            <div className="w-9 h-9 rounded bg-[#FFD814] flex items-center justify-center text-[#131921] font-bold shadow-sm">
              <Wrench className="w-5 h-5 text-[#131921]" />
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <span className="text-xl font-bold tracking-tight text-white font-['Hanken_Grotesk']">
                  ResolveAI
                </span>
                <span className="text-xs text-[#8A97A9] border-l border-[#44474C] pl-2 hidden sm:inline">
                  Customer Repair Assistant
                </span>
              </div>
              <div className="flex items-center gap-1 text-[#8A97A9] text-xs">
                <MapPin className="w-3 h-3 text-[#FF9900]" />
                <span>Consumer Repair Resolution Workspace</span>
              </div>
            </div>
          </div>

          {/* Search Bar - Amazon Utility Style */}
          <div className="flex-1 max-w-2xl hidden md:flex items-center">
            <div className="w-full flex rounded overflow-hidden focus-within:ring-2 focus-within:ring-[#007185]">
              <button
                type="button"
                className="h-9 px-3 bg-[#EEEEED] text-[#0F1111] text-xs font-semibold flex items-center gap-1 border-r border-[#D5D9D9] hover:bg-[#E8E8E7]"
              >
                <span>Cases</span>
              </button>
              <input
                type="text"
                placeholder="Search cases, warranty receipts, repair centers, or ask ResolveAI..."
                className="w-full h-9 px-3 bg-white text-[#0F1111] text-sm focus:outline-none placeholder:text-[#75777C]"
              />
              <button
                type="button"
                className="h-9 px-4 bg-[#FFD814] hover:bg-[#F7CA00] text-[#0F1111] flex items-center justify-center transition-colors"
                title="Search"
              >
                <Search className="w-4 h-4 text-[#0F1111]" />
              </button>
            </div>
          </div>

          {/* Right Links & Profile */}
          <div className="flex items-center gap-4 text-xs">
            <button
              onClick={onNewCaseClick}
              className="h-9 px-3 bg-[#FFD814] hover:bg-[#F7CA00] text-[#0F1111] font-bold text-xs rounded border border-[#FCD200] shadow-sm flex items-center gap-1.5 transition-all"
            >
              <PlusCircle className="w-4 h-4 text-[#0F1111]" />
              <span>Start New Case</span>
            </button>

            <div className="hidden lg:flex items-center gap-1 text-[#8A97A9] hover:text-white cursor-pointer">
              <Globe className="w-4 h-4" />
              <span className="font-semibold text-white">EN</span>
            </div>

            <div className="flex items-center gap-2 pl-2 border-l border-[#37475A]">
              <div className="w-7 h-7 rounded-full bg-[#232F3E] border border-[#565959] flex items-center justify-center text-white">
                <User className="w-4 h-4" />
              </div>
              <div className="hidden sm:flex flex-col text-left leading-tight">
                <span className="text-[#8A97A9] text-[10px]">ResolveAI Demo</span>
                <span className="font-bold text-white text-xs">Account & Workspace</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Secondary Navy Nav Strip */}
      <div className="bg-[#232F3E] text-white border-t border-[#131921]/60">
        <div className="max-w-[1400px] mx-auto px-4 lg:px-8 h-10 flex items-center justify-between text-xs font-semibold">
          <nav className="flex items-center gap-1 overflow-x-auto no-scrollbar">
            <button
              onClick={() => onTabChange('home')}
              className={`px-3 py-1 rounded transition-colors whitespace-nowrap ${
                currentTab === 'home'
                  ? 'bg-[#131921] text-[#FFE16B] font-bold'
                  : 'text-[#BBC7DB] hover:text-white hover:bg-[#131921]/50'
              }`}
            >
              Home / Dashboard
            </button>

            <button
              onClick={() => onTabChange('cases')}
              className={`px-3 py-1 rounded transition-colors whitespace-nowrap ${
                currentTab === 'cases'
                  ? 'bg-[#131921] text-[#FFE16B] font-bold'
                  : 'text-[#BBC7DB] hover:text-white hover:bg-[#131921]/50'
              }`}
            >
              My Cases
            </button>

            {activeCaseId && (
              <button
                onClick={() => onTabChange('case-details')}
                className={`px-3 py-1 rounded transition-colors whitespace-nowrap ${
                  currentTab === 'case-details'
                    ? 'bg-[#131921] text-[#FFE16B] font-bold'
                    : 'text-[#BBC7DB] hover:text-white hover:bg-[#131921]/50'
                }`}
              >
                Active Case: {activeCaseId.slice(0, 8)}...
              </button>
            )}

            <button
              onClick={() => onTabChange('follow-ups')}
              className={`px-3 py-1 rounded transition-colors whitespace-nowrap ${
                currentTab === 'follow-ups'
                  ? 'bg-[#131921] text-[#FFE16B] font-bold'
                  : 'text-[#BBC7DB] hover:text-white hover:bg-[#131921]/50'
              }`}
            >
              Scheduled Follow-ups
            </button>
          </nav>

          <div className="hidden sm:flex items-center gap-2 bg-[#131921] px-2.5 py-1 rounded text-[11px] text-[#8A97A9] border border-[#37475A]">
            <span className="w-2 h-2 rounded-full bg-[#FFD814] animate-pulse" />
            <span>Developer Hackathon Demo Prototype</span>
          </div>
        </div>
      </div>
    </header>
  )
}
