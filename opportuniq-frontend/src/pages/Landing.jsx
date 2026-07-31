import FeaturesSection from '../components/common/FeaturesSection'
import HeroSection from '../components/common/HeroSection'
import Footer from '../components/layout/Footer'
import Navbar from '../components/layout/Navbar'

export default function Landing() {
  return (
    <div className="landing-page">
      <Navbar />
      <main>
        <HeroSection />
        <FeaturesSection />
      </main>
      <Footer />
    </div>
  )
}
