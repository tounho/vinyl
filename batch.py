import sys
import os
import configparser
import glob
import textwrap
import multiprocessing
import subprocess
from xml.dom import minidom
from PIL import Image, ImageFont, ImageDraw

_DEBUG = False

vinyl_path = os.path.abspath('./x64/Release/vinyl.exe')
inkscape_path = os.path.abspath('../inkscape/inkscape.exe')

def worker(job):
    if job['cache'] and os.path.exists(job['svg_path']):
        print('#{id} {name} already exists. Skipped.'.format(
            id=job['id'],
            name=os.path.basename(job['svg_path'])
            ))
        sys.stdout.flush()
    else:
        cmd = '"{vinyl}" "{file}"{s}{c}{r}{p}'.format(
            vinyl=vinyl_path,
            file=job['video_path'],
            c=' --crop={c}'.format(c=job['crop']) if job['crop'] else '',
            s=' --scale={s}'.format(s=job['scale']) if job['scale'] else '',
            r=' -r {range}'.format(range=job['radius']) if job['radius'] else '',
            p=' -p' if job['preview'] else ''
            )
    
        p = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
        p.communicate()
        print('#{id} {name} finished.'.format(
            id=job['id'],
            name=os.path.basename(job['svg_path'])
            ))
        sys.stdout.flush()

    if job['cache'] and os.path.exists(job['png_path']):
        dimension = int(minidom.parse(job['svg_path']).getElementsByTagName("svg")[0].getAttribute('viewBox').split(' ')[3]) * job['dimensionmultiplier']
        print('#{id} {name} already exists. Skipped.'.format(
            id=job['id'],
            name=os.path.basename(job['png_path'])
            ))
        sys.stdout.flush()
        job['dimension'] = dimension
        return job
    else:
        dimension = int(minidom.parse(job['svg_path']).getElementsByTagName("svg")[0].getAttribute('viewBox').split(' ')[3]) * job['dimensionmultiplier']
        cmd = '"{inkscape}" --file="{svg}" --without-gui --export-png="{png}" --export-height={height}'.format(
            inkscape=inkscape_path,
            svg=job['svg_path'],
            png=job['png_path'],
            height=dimension
            )

        p = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
        p.communicate()
        print('#{id} {name} finished.'.format(
            id=job['id'],
            name=os.path.basename(job['png_path'])
            ))
        sys.stdout.flush()
        job['dimension'] = dimension
        return job

if __name__ == '__main__':
    # target directory
    if len(sys.argv) < 2 or not os.path.isdir(sys.argv[1]):
        print('No valid directory provided.')
        exit();

    dir = os.path.abspath(sys.argv[1])
    config_ini =  os.path.join(dir, 'config.ini')

    # config
    config = configparser.ConfigParser()
    # default values
    config['ROOT'] = {
            'cache': 'true',
            'threads': 4,
            'reversefiles': 'false',

            'title': '',
            'extensions': 'mkv, mp4',
            'columnwidths': '',

            'crop': '',
            'scale': '-1,144',
            'radius': 10,
            'preview': 'true',

            'dimensionmultiplier': 10,

            'textwrap': 32,
            'padding': 20,
            'font': 'Arial Unicode MS.ttf',
            'title_pt': 96,
            'subtitle_pt': 64,
            'title_outline': 4,
            'subtitle_outline': 3
            

        }
    # create new config.ini in dir.
    if not os.path.exists(config_ini):
        config.write(open(os.path.join(dir, 'config.ini'), 'w'))
        input('New config.ini created. Press Enter to continue...')
    # read or re-read config.ini
    config.read(config_ini)

    # create a list of all videos to preocess
    video_paths = []
    for ext in config['ROOT']['extensions'].replace(' ', '').split(','):
        video_paths.extend(glob.glob(os.path.join(dir, '*.' + ext)))
    video_paths = sorted(
        video_paths,
        key=lambda k: os.path.splitext(os.path.basename(k))[0].lower(),
        reverse=(config['ROOT']['reversefiles'].lower() == 'true')
        )
    print('{n} video files found in {dir}'.format(n=len(video_paths), dir=dir))
    
    # title
    title = config['ROOT']['title'].replace(r'\n', '\n');
    print('Title: {title}'.format(title=title) if title else 'No title provided.')

    # read subtitle file
    subtitles = []
    if os.path.exists(os.path.join(dir, 'subtitles.txt')):
        fp = open(os.path.join(dir, 'subtitles.txt'), encoding='utf-8')
        subtitles = [ textwrap.fill(
            line.rstrip().replace(r'\n', '\n'),
            int(config['ROOT']['textwrap']) if config['ROOT']['textwrap'].isnumeric() and int(config['ROOT']['textwrap']) > 0 else 1e9,
            replace_whitespace=False
            ) for line in fp ]
    print('{n} subtitles provided.'.format(n = len(subtitles) if len(subtitles) else 'No'))

    # read number of columns per row
    column_widths = [ int(line) for line in config['ROOT']['columnwidths'].replace(' ', '').split(',') if line.isnumeric()]
    if (sum(column_widths) > len(video_paths)):
        print('Sum of all columnwidths in config.ini too big. Sum must be less than or equal to {n}'.format(n=len(video_paths)))
        exit()
    elif (sum(column_widths) < len(video_paths)):
        column_widths.append(len(video_paths) - sum(column_widths))
        print('Sum of all columnwidths in config.ini too small. Appended with {n}'.format(n=column_widths[-1]))

    # create job list
    jobs = []
    for i, p in enumerate(video_paths):
        jobs.append({
            'id': i,
            'video_path': p,
            'svg_path': os.path.join(dir, os.path.splitext(os.path.basename(p))[0] + '.svg'),
            'png_path': os.path.join(dir, os.path.splitext(os.path.basename(p))[0] + '.png'),
            'subtitle': subtitles[i] if len(subtitles) > i else '',
            'cache': (config['ROOT']['cache'].lower() == 'true'),
            'crop': config['ROOT']['crop'],
            'scale': config['ROOT']['scale'],
            'radius': int(config['ROOT']['radius']) if config['ROOT']['cache'].isnumeric() else 0,
            'preview': (config['ROOT']['preview'].lower() == 'true'),
            'dimensionmultiplier': int(config['ROOT']['dimensionmultiplier']) if config['ROOT']['dimensionmultiplier'].isnumeric() and int(config['ROOT']['dimensionmultiplier']) > 0 else 1
            })

    # Pool for multithreading
    pool = multiprocessing.Pool(int(config['ROOT']['threads']) if config['ROOT']['threads'].isnumeric() and int(config['ROOT']['threads']) > 0 else 1)

    print('Rendering...')
    sys.stdout.flush()
    jobs = pool.map(worker, jobs)
    print('Done!')

    print('Drawing composite image...')
    sys.stdout.flush()
    padding = int(config['ROOT']['padding']) if config['ROOT']['padding'].isnumeric() else 0
    vinyl_dimension = max(jobs, key=lambda k: k['dimension'])['dimension']
    rows = len(column_widths)
    max_columns = max(column_widths)
    
    ttf = config['ROOT']['font']

    title_pt = int(config['ROOT']['title_pt'])
    subtitle_pt = int(config['ROOT']['subtitle_pt'])
    
    title_outline = int(config['ROOT']['title_outline'])
    subtitle_outline = int(config['ROOT']['subtitle_outline'])

    title_font = ImageFont.truetype(ttf, title_pt)
    subtitle_font = ImageFont.truetype(ttf, subtitle_pt)

    null_draw = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    title_height = null_draw.multiline_textsize(title + '\n', title_font)[1] + padding if title else 0
    subtitle_height = max([ null_draw.multiline_textsize(job['subtitle'] + '\n', subtitle_font)[1] for job in jobs ]) + padding if len(subtitles) else 0

    canvas = Image.new(
        mode='RGBA',
        size=(
            padding + (vinyl_dimension + padding) * max_columns,
            padding + title_height + (vinyl_dimension + subtitle_height + padding) * rows
            ),
        color=(255, 255, 255, 0)
        )
    draw = ImageDraw.Draw(canvas)

    if _DEBUG: draw.rectangle((0, 0, canvas.width, canvas.height), None, (0, 0, 0), 5)

    if title:
        w, h = draw.multiline_textsize(title, title_font)
        draw.text(
            (canvas.width/2 - w/2, padding),
            title,
            fill=(255, 255, 255),
            font=title_font,
            stroke_width=title_outline,
            stroke_fill=(20, 20, 20),
            align='center'
            )

        if _DEBUG: draw.rectangle((canvas.width/2 - w/2,padding, canvas.width/2 - w/2 + w, padding + h), None, (0, 0, 0), 3)
        if _DEBUG: draw.line((0, padding + title_height, canvas.width, padding + title_height), (120, 0, 0), 5)

    for r, columns in enumerate(column_widths):
        offset_y = int(padding + title_height + r * (vinyl_dimension + padding + subtitle_height))
        if _DEBUG: draw.line((0, offset_y, canvas.width, offset_y), (0, 200, 0), 5)
        for c in range(columns):
            i = sum(column_widths[:r]) + c
            offset_x = int((canvas.width - columns * vinyl_dimension - (columns-1)*padding)/2 + c * (vinyl_dimension + padding))

            vinyl = Image.open(jobs[i]['png_path'])
            canvas.paste(vinyl, (int(offset_x + (vinyl_dimension - vinyl.width) / 2), int(offset_y + (vinyl_dimension - vinyl.height) / 2)))

            w, h = draw.multiline_textsize(jobs[i]['subtitle'], subtitle_font)
            draw.text(
                (offset_x + vinyl_dimension / 2 - w / 2, offset_y + vinyl_dimension + padding),
                jobs[i]['subtitle'],
                fill=(255, 255, 255),
                font=subtitle_font,
                stroke_width=subtitle_outline,
                stroke_fill=(20, 20, 20),
                align='center'
                )

            if _DEBUG: draw.rectangle((offset_x, offset_y, offset_x + vinyl_dimension, offset_y + vinyl_dimension), None, (0, 0, 0), 3)
            if _DEBUG: draw.rectangle((offset_x + vinyl_dimension / 2 - w / 2, offset_y + vinyl_dimension + padding, offset_x + vinyl_dimension / 2 + w / 2, offset_y + vinyl_dimension + padding + h), None, (0, 0, 0), 3)
            
    print('Done!')
    sys.stdout.flush()
    canvas.save(os.path.join(dir, 'vinyl.png'))
    print('Saved at {path}'.format(path=os.path.join(dir, 'vinyl.png')))