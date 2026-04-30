import Navbar from "@/components/navbar"
import Footer from "@/components/footer"

export default function About() {
  return (
    <div className="min-h-screen bg-white flex flex-col">
      <Navbar />

      <main className="flex-1">
        <section className="w-full max-w-4xl mx-auto px-4 md:px-8 py-16 md:py-24">
          <h1 className="text-4xl md:text-5xl font-serif font-bold text-center mb-12">About Farm One</h1>

          <div className="prose prose-lg max-w-none">
            <p className="text-gray-700 leading-relaxed text-center">
              Farm One is a minimalist platform designed to help farmers make informed decisions about crop selection
              and cultivation. By integrating real-time weather data from Open-Meteo and soil information from
              SoilGrids, our platform provides clean, actionable insights for your location. Simply select your
              coordinates on the map, and Farm One will deliver comprehensive analysis of your agricultural potential.
              Our commitment to simplicity and accuracy ensures you have the clarity needed to optimize your farming
              practices.
            </p>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  )
}
