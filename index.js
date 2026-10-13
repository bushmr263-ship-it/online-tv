addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  // এখানে আপনার বিটলি লিংকটি বসিয়ে দিন
  const targetUrl = "https://bit.ly/3SdW560"

  try {
    // মূল source থেকে response fetch করা (redirect ফলো করার জন্য redirect: 'follow' যুক্ত করা ভালো)
    const userAgent = request.headers.get("User-Agent") || "Mozilla/5.0 (Windows NT 10.0; Win64; x64)";
    
    const response = await fetch(targetUrl, {
      headers: {
        "User-Agent": userAgent,
        "Referer": "https://mycoffeetime.net/"
      },
      redirect: 'follow'
    });

    // যদি token expire বা fail করে, তবে handle করার logic
    if (response.status === 403 || response.status === 401) {
      return new Response("Token Expired. Please update the new token link.", { status: 401 });
    }

    // CORS header যুক্ত করে client-ে return করা
    const newResponse = new Response(response.body, response);
    newResponse.headers.set("Access-Control-Allow-Origin", "*");
    return newResponse;

  } catch (err) {
    return new Response("Error fetching stream: " + err.message, { status: 500 });
  }
}
